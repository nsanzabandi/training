# === Core Imports ===
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, FileResponse, Http404
from django.urls import reverse
from django.core.mail import send_mail, BadHeaderError
from django.db import IntegrityError, transaction
from django.utils.timezone import now
from django.conf import settings
from django.template.loader import get_template
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages


import os
import csv
import io
import smtplib
import uuid
import qrcode
import logging

# === App Imports ===
from .models import Staff, Training, Participant, Department, Enrollment, TrainingDocument, District
from .forms import (UserUpdateForm, TrainingForm, ParticipantForm, DepartmentForm,
    EnrollmentForm, StaffSignupForm, QuickInviteForm)

from .utils import admin_required, get_staff_for_user
from xhtml2pdf import pisa

logger = logging.getLogger(__name__)

# === Dashboard Views ===
@login_required
def dashboard(request):
    staff = request.user

    if not staff.active or not staff.role:
        messages.warning(request, "Your account is pending approval. Please wait for admin activation.")
        return redirect('pending_approval')

    if staff.role == 'admin':
        trainings = Training.objects.all()
    elif staff.role == 'supervisor':
        trainings = Training.objects.filter(coordinator=staff)
    else:
        trainings = Training.objects.filter(department=staff.department)

    enrollments = Enrollment.objects.filter(training__in=trainings)
    participants = Participant.objects.all()
    if staff.role == 'regular':
        participants = participants.filter(department=staff.department)

    training_stats = {
        t.id: {
            'confirmed': t.enrollment_set.filter(confirmation_status='confirmed').count(),
            'pending': t.enrollment_set.filter(confirmation_status='pending').count(),
            'total': t.enrollment_set.count()
        }
        for t in trainings
    }

    context = {
        'staff': staff,
        'trainings': trainings,
        'training_stats': training_stats,
        'total_trainings': trainings.count(),
        'pending_trainings': trainings.filter(status='pending').count(),
        'total_confirmed': enrollments.filter(confirmation_status='confirmed').count(),
        'total_participants': participants.count(),
        'chart_labels': [t.title for t in trainings],
        'chart_data': [t.enrollment_set.filter(confirmation_status='confirmed').count() for t in trainings],
    }

    if staff.role == 'admin':
        return render(request, 'trainings/admin_dashboard.html', context)
    elif staff.role == 'supervisor':
        return render(request, 'trainings/supervisor_dashboard.html', context)
    else:
        return render(request, 'trainings/regular_dashboard.html', context)

@login_required
def supervisor_dashboard(request):
    staff = request.user
    trainings = Training.objects.filter(coordinator=staff)
    enrollments = Enrollment.objects.filter(training__in=trainings)

    context = {
        'staff': staff,
        'trainings': trainings,
        'total_trainings': trainings.count(),
        'total_participants': enrollments.values('participant').distinct().count(),
        'total_confirmed': enrollments.filter(confirmation_status='confirmed').count(),
    }

    return render(request, 'trainings/supervisor_dashboard.html', context)

# === Authentication Views ===
def custom_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            try:
                existing_user = get_user_model().objects.get(username=username)
                if not existing_user.is_active:
                    messages.warning(request, "Your account is pending approval. Please wait for admin activation.")
                else:
                    messages.error(request, "Invalid username or password. Please try again.")
            except get_user_model().DoesNotExist:
                messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = AuthenticationForm()

    return render(request, 'trainings/login.html', {'form': form})

@login_required
def custom_logout(request):
    logger.debug(f"Logging out user: {request.user.username}")
    request.session.flush()
    logout(request)
    request.session.modified = True
    messages.success(request, "You have been logged out.")
    return redirect('login')

def pending_approval(request):
    return render(request, 'trainings/pending_approval.html')

# === Basic Utility Views ===
@login_required
def thank_you_page(request):
    training_title = request.session.pop('submitted_training', None)
    return render(request, 'trainings/thank_you.html', {
        'training_title': training_title
    })

@login_required
def load_districts(request):
    province_id = request.GET.get('province_id')
    districts = District.objects.filter(province_id=province_id).order_by('name')
    return JsonResponse(list(districts.values('id', 'name')), safe=False)

@login_required
def delete_training_document(request, doc_id):
    doc = get_object_or_404(TrainingDocument, id=doc_id)
    training_id = doc.training.id

    if request.method == 'POST':
        doc.file.delete()
        doc.delete()
        messages.success(request, "Document deleted successfully.")

    return redirect('training_edit', pk=training_id)

# === Admin Actions ===
@login_required
@require_POST
def reject_training_with_reason(request, training_id):
    training = get_object_or_404(Training, id=training_id)

    if request.user.role != 'admin':
        messages.error(request, "You are not authorized to reject this training.")
        return redirect('dashboard')

    reason = request.POST.get('rejection_reason')
    if reason:
        training.status = 'rejected'
        training.rejection_reason = reason
        training.save()
        messages.success(request, "Training rejected with reason.")
    else:
        messages.error(request, "Rejection reason is required.")

    return redirect('dashboard')


# === Training Views ===

@login_required
def training_list(request):
    staff = request.user
    query = request.GET.get('q')

    if staff.role == 'admin':
        trainings = Training.objects.all()
    elif staff.role == 'supervisor':
        trainings = Training.objects.filter(coordinator=staff)
    else:
        trainings = Training.objects.filter(department=staff.department)

    if query:
        trainings = trainings.filter(Q(title__icontains=query) | Q(department__name__icontains=query))

    return render(request, 'trainings/training_list.html', {
        'trainings': trainings,
        'staff': staff
    })


@login_required
def training_create(request):
    staff = request.user

    # ✅ Only Admin or Regular can create training
    if staff.role not in ['admin', 'regular']:
        messages.error(request, "You are not authorized to create a training.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = TrainingForm(request.POST, request.FILES, user=staff)
        files = request.FILES.getlist('documents')

        if form.is_valid():
            training = form.save(commit=False)
            training.created_by = staff
            if staff.role == 'regular':
                training.department = staff.department
            training.save()

            for file in files:
                if file.name.lower().endswith(('.pdf', '.doc', '.docx')) and file.size <= 10 * 1024 * 1024:
                    TrainingDocument.objects.create(training=training, file=file)

            messages.success(request, "Training created successfully.")
            return redirect('training_list')
        else:
            messages.error(request, "Form submission failed. Please fix the errors.")
    else:
        form = TrainingForm(user=staff)
        if staff.role == 'regular':
            form.fields['department'].queryset = Department.objects.filter(id=staff.department.id)
            form.fields['department'].initial = staff.department
            form.fields['department'].widget.attrs['readonly'] = True

    return render(request, 'trainings/training_form.html', {'form': form, 'staff': staff})



@login_required
def training_edit(request, pk):
    training = get_object_or_404(Training, pk=pk)
    staff = request.user

    if staff != training.created_by and staff.role != 'admin':
        messages.error(request, "You are not authorized to edit this training.")
        return redirect('training_list')

    if request.method == 'POST':
        form = TrainingForm(request.POST, request.FILES, instance=training, user=staff)
        files = request.FILES.getlist('documents')

        if form.is_valid():
            training = form.save(commit=False)
            training.status = 'pending'  # Reset to pending
            training.rejection_reason = None
            training.save()

            for file in files:
                if file.name.lower().endswith(('.pdf', '.doc', '.docx')) and file.size <= 10 * 1024 * 1024:
                    TrainingDocument.objects.create(training=training, file=file)

            messages.success(request, "Training updated and sent for re-approval.")
            return redirect('training_list')
        else:
            messages.error(request, "Form has errors.")
    else:
        form = TrainingForm(instance=training, user=staff)

    documents = training.documents.all()
    return render(request, 'trainings/training_edit_form.html', {
        'form': form,
        'staff': staff,
        'training': training,
        'documents': documents,
    })


@login_required
def training_delete(request, pk):
    training = get_object_or_404(Training, pk=pk)
    staff = request.user

    if staff == training.created_by or staff.role == 'admin':
        training.delete()
        messages.success(request, "Training deleted successfully.")
    else:
        messages.error(request, "You are not authorized to delete this training.")

    return redirect('training_list')



@login_required
def approve_training(request, training_id):
    staff = request.user
    if staff.role == 'admin':
        training = get_object_or_404(Training, id=training_id)
        training.status = 'approved'
        training.save()
        messages.success(request, "Training approved.")
    return redirect('dashboard')


@login_required
def reject_training(request, training_id):
    staff = request.user
    if staff.role == 'admin':
        training = get_object_or_404(Training, id=training_id)
        training.status = 'rejected'
        training.save()
        messages.success(request, "Training rejected.")
    return redirect('dashboard')

# === Participant Views ===

@login_required
def participant_list(request):
    staff = request.user
    query = request.GET.get('q')

    if staff.role == 'regular':
        participants = Participant.objects.filter(department=staff.department)
    else:
        participants = Participant.objects.all()

    if query:
        participants = participants.filter(
            Q(full_name__icontains=query) |
            Q(email__icontains=query) |
            Q(department__name__icontains=query)
        )

    return render(request, 'trainings/participant_list.html', {
        'participants': participants,
        'staff': staff
    })


@login_required
def participant_create(request):
    staff = request.user

    if request.method == 'POST':
        form = ParticipantForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Participant created successfully.")
            return redirect('participant_list')
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = ParticipantForm(user=request.user)

    return render(request, 'trainings/participant_form.html', {
        'form': form,
        'staff': staff
    })


@login_required
def participant_edit(request, pk):
    participant = get_object_or_404(Participant, pk=pk)
    staff = request.user

    if staff.role == 'regular' and participant.department != staff.department:
        messages.error(request, "You are not allowed to edit this participant.")
        return redirect('participant_list')

    if request.method == 'POST':
        form = ParticipantForm(request.POST, instance=participant, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Participant updated successfully.")
            return redirect('participant_list')
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = ParticipantForm(instance=participant, user=request.user)

    return render(request, 'trainings/participant_form.html', {
        'form': form,
        'staff': staff
    })


@login_required
def participant_delete(request, pk):
    participant = get_object_or_404(Participant, pk=pk)
    staff = request.user

    if staff.role == 'regular' and participant.department != staff.department:
        messages.error(request, "You are not allowed to delete this participant.")
        return redirect('participant_list')

    participant.delete()
    return redirect('participant_list')


@login_required
def participant_detail(request, participant_id):
    participant = get_object_or_404(Participant, national_id=participant_id)
    enrollments = Enrollment.objects.filter(participant=participant)
    return render(request, 'trainings/participant_detail.html', {
        'participant': participant,
        'enrollments': enrollments
    })


@login_required
def participant_pdf_report(request, participant_id):
    participant = get_object_or_404(Participant, id=participant_id)
    enrollments = Enrollment.objects.filter(participant=participant)

    for e in enrollments:
        if isinstance(e.training.start_date, str):
            e.training.start_date = datetime.strptime(e.training.start_date, "%Y-%m-%d").date()
        if isinstance(e.training.end_date, str):
            e.training.end_date = datetime.strptime(e.training.end_date, "%Y-%m-%d").date()
        e.total_days = (e.training.end_date - e.training.start_date).days + 1

    qr_data = f"Participant ID: {participant.id} | Name: {participant.full_name}"
    qr_img = qrcode.make(qr_data)
    qr_filename = f"qr_{participant.id}.png"
    qr_path = os.path.join(settings.STATICFILES_DIRS[0], 'img', qr_filename)
    qr_img.save(qr_path)

    template = get_template('trainings/participant_pdf.html')
    html = template.render({
        'participant': participant,
        'enrollments': enrollments,
        'qr_code_path': f'/static/img/{qr_filename}',
    })

    def link_callback(uri, rel):
        static_url = settings.STATIC_URL
        static_root = settings.STATIC_ROOT or os.path.join(settings.BASE_DIR, 'static')
        if uri.startswith(static_url):
            path = os.path.join(static_root, uri.replace(static_url, ''))
            return path
        return uri

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{participant.full_name}_report.pdf"'

    pisa_status = pisa.CreatePDF(io.BytesIO(html.encode('UTF-8')), dest=response, link_callback=link_callback)

    if pisa_status.err:
        return HttpResponse('PDF error <pre>' + html + '</pre>')
    return response


# === Enrollment Views ===

@login_required
def enrollment_list(request):
    staff = request.user
    query = request.GET.get('q')

    enrollments = Enrollment.objects.all()
    if query:
        enrollments = enrollments.filter(
            Q(participant__full_name__icontains=query) |
            Q(training__title__icontains=query)
        )

    return render(request, 'trainings/enrollment_list.html', {
        'enrollments': enrollments,
        'staff': staff
    })


@login_required
def enrollment_create(request):
    staff = request.user

    if request.method == 'POST':
        form = EnrollmentForm(request.POST, user=request.user)
        if form.is_valid():
            enrollment = form.save(commit=False)
            enrollment.enrolled_by = staff
            if enrollment.confirmation_status == 'confirmed':
                enrollment.confirmation_date = now()
            enrollment.save()

            confirm_url = request.build_absolute_uri(
                reverse('confirm_enrollment', args=[str(enrollment.invite_token)])
            )

            try:
                send_mail(
                    subject='Training Confirmation',
                    message=f"""Dear {enrollment.participant.full_name},\n\nPlease confirm your attendance for '{enrollment.training.title}' by clicking the link below:\n{confirm_url}""",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[enrollment.participant.email],
                    fail_silently=False,
                )
                messages.success(request, 'Enrollment created and confirmation email sent.')
            except (smtplib.SMTPException, BadHeaderError):
                messages.warning(request, "Enrollment saved but confirmation email failed.")

            return redirect('enrollment_list')
    else:
        form = EnrollmentForm(user=request.user)

    return render(request, 'trainings/enrollment_form.html', {
        'form': form,
        'staff': staff
    })


@login_required
def enrollment_invite_form(request, token):
    enrollment = get_object_or_404(Enrollment, invite_token=token)
    participant = enrollment.participant

    if request.method == 'POST':
        form = ParticipantForm(request.POST, request.FILES, instance=participant)
        if form.is_valid():
            participant = form.save()

            if enrollment.confirmation_status != 'confirmed':
                enrollment.confirmation_status = 'confirmed'
                enrollment.confirmation_date = now()
                enrollment.save()

            messages.success(request, "Your information has been submitted successfully.")
            request.session['submitted_training'] = enrollment.training.title
            return redirect('thank_you')
    else:
        form = ParticipantForm(instance=participant)

    return render(request, 'trainings/enrollment_invite_form.html', {
        'form': form,
        'participant': participant,
        'training': enrollment.training
    })


@login_required
def confirm_enrollment(request, token):
    enrollment = get_object_or_404(Enrollment, invite_token=token)

    if enrollment.confirmation_status != 'confirmed':
        enrollment.confirmation_status = 'confirmed'
        enrollment.confirmation_date = now()
        enrollment.save()

    return render(request, 'trainings/confirmation_success.html', {
        'participant': enrollment.participant,
        'training': enrollment.training,
    })


@login_required
def participant_training_history(request, national_id):
    try:
        participant = Participant.objects.get(national_id=national_id)
    except Participant.DoesNotExist:
        return JsonResponse({'error': 'Participant not found.'}, status=404)

    enrollments = Enrollment.objects.filter(participant=participant).select_related('training')

    if not enrollments.exists():
        return JsonResponse({'participant': participant.full_name, 'enrollments': [], 'debug': 'No enrollments found.'})

    data = {
        'participant': participant.full_name,
        'enrollments': [
            {
                'participant_id': e.participant.national_id,
                'training_title': e.training.title,
                'start_date': e.training.start_date.strftime('%Y-%m-%d'),
                'end_date': e.training.end_date.strftime('%Y-%m-%d'),
                'attendance_status': e.attendance_status,
            }
            for e in enrollments
        ]
    }

    return JsonResponse(data)

# === Staff, Department, Auth, and Remaining Views ===

# --- Staff Views ---
@login_required
@admin_required
def staff_list(request):
    query = request.GET.get('q')
    staff_members = Staff.objects.all()

    if query:
        staff_members = staff_members.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(department__name__icontains=query) |
            Q(role__icontains=query)
        )

    return render(request, 'trainings/staff_list.html', {
        'staff_members': staff_members,
        'staff': request.user
    })



@login_required
@admin_required
def staff_create(request):
    if request.method == 'POST':
        form = StaffSignupForm(request.POST, request.FILES)
        if form.is_valid():
            staff = form.save(commit=False)
            staff.active = False  # Adjust as needed
            staff.save()
            messages.success(request, "Staff created. Awaiting approval.")
            return redirect('staff_list')
    else:
        form = StaffSignupForm()

    return render(request, 'trainings/staff_form.html', {'form': form, 'staff': request.user})


@login_required
@admin_required
def staff_edit(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    if request.method == 'POST':
        form = StaffSignupForm(request.POST, request.FILES, instance=staff)
        if form.is_valid():
            form.save()
            messages.success(request, "Staff member updated.")
            return redirect('staff_list')
    else:
        form = StaffSignupForm(instance=staff)

    return render(request, 'trainings/staff_form.html', {'form': form, 'editing': True})


@login_required
@admin_required
def approve_staff(request, staff_id):
    staff = get_object_or_404(Staff, pk=staff_id)
    
    staff.active = True
    staff.is_active = True   # ✅ Important for Django login
    if staff.role == 'admin':
        staff.is_staff = True  # ✅ Admins are staff
        staff.is_superuser = False  # Optional: depends if you want
    staff.save()

    messages.success(request, f"{staff.get_full_name()} approved and activated.")
    return redirect('staff_list')




@login_required
@admin_required
def staff_delete(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    staff.delete()
    messages.success(request, "Staff member deleted.")
    return redirect('staff_list')


# --- Department Views ---
@login_required
@admin_required
def department_list(request):
    query = request.GET.get('q')
    departments = Department.objects.all()
    if query:
        departments = departments.filter(name__icontains=query)

    return render(request, 'trainings/department_list.html', {'departments': departments, 'staff': request.user})


@login_required
@admin_required
def department_create(request):
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('department_list')
    else:
        form = DepartmentForm()

    return render(request, 'trainings/department_form.html', {'form': form, 'staff': request.user})


@login_required
@admin_required
def department_edit(request, pk):
    department = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            return redirect('department_list')
    else:
        form = DepartmentForm(instance=department)

    return render(request, 'trainings/department_form.html', {'form': form, 'staff': request.user})


@login_required
@admin_required
def department_delete(request, pk):
    department = get_object_or_404(Department, pk=pk)
    department.delete()
    return redirect('department_list')


# --- Auth Views ---
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login, logout

def register(request):
    if request.method == 'POST':
        form = StaffSignupForm(request.POST, request.FILES)
        if form.is_valid():
            staff = form.save(commit=False)
            staff.active = False
            staff.save()
            messages.success(request, "Account created. Awaiting approval.")
            return redirect('login')
    else:
        form = StaffSignupForm()
    return render(request, 'trainings/register.html', {'form': form})


@login_required
def custom_logout(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('login')


def pending_approval(request):
    return render(request, 'trainings/pending_approval.html')


def custom_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            User = get_user_model()
            try:
                existing_user = User.objects.get(username=username)
                if not existing_user.is_active:
                    messages.warning(request, "Your account is pending approval.")
                else:
                    messages.error(request, "Invalid login credentials.")
            except User.DoesNotExist:
                messages.error(request, "Invalid login credentials.")
    else:
        form = AuthenticationForm()

    return render(request, 'trainings/login.html', {'form': form})


# --- Remaining Views (District loader and file deletion) ---
@login_required
def load_districts(request):
    province_id = request.GET.get('province_id')
    districts = District.objects.filter(province_id=province_id).order_by('name')
    return JsonResponse(list(districts.values('id', 'name')), safe=False)


@login_required
def delete_training_document(request, doc_id):
    doc = get_object_or_404(TrainingDocument, id=doc_id)
    training_id = doc.training.id
    if request.method == 'POST':
        doc.file.delete()
        doc.delete()
        messages.success(request, "Document deleted successfully.")
    return redirect('training_edit', pk=training_id)


@login_required
@require_POST
def reject_training_with_reason(request, training_id):
    training = get_object_or_404(Training, id=training_id)
    if request.user.role != 'admin':
        messages.error(request, "Unauthorized.")
        return redirect('dashboard')

    reason = request.POST.get('rejection_reason')
    if reason:
        training.status = 'rejected'
        training.rejection_reason = reason
        training.save()
        messages.success(request, "Training rejected.")
    else:
        messages.error(request, "Rejection reason required.")

    return redirect('dashboard')


@login_required
def participant_training_history(request, national_id):
    try:
        participant = Participant.objects.get(national_id=national_id)
    except Participant.DoesNotExist:
        return JsonResponse({'error': 'Participant not found.'}, status=404)

    enrollments = Enrollment.objects.filter(participant=participant).select_related('training')

    data = {
        'participant': participant.full_name,
        'enrollments': [
            {
                'participant_id': e.participant.national_id,
                'training_title': e.training.title,
                'start_date': e.training.start_date.strftime('%Y-%m-%d'),
                'end_date': e.training.end_date.strftime('%Y-%m-%d'),
                'attendance_status': e.attendance_status,
            }
            for e in enrollments
        ]
    }

    return JsonResponse(data)

@login_required
def mark_attendance(request, training_id):
    training = get_object_or_404(Training, id=training_id)

    # ✅ Allow admin, creator or coordinator to mark attendance
    if not (request.user.is_superuser or request.user == training.created_by or request.user == training.coordinator):
        messages.error(request, "You are not authorized to mark attendance for this training.")
        return redirect('dashboard')

    enrollments = Enrollment.objects.filter(training=training)

    if request.method == 'POST':
        for enrollment in enrollments:
            status = request.POST.get(f'attendance_{enrollment.id}')
            if status:
                enrollment.attendance_status = status
                enrollment.save()

        messages.success(request, "Attendance updated successfully.")
        return redirect('training_attendance_summary', training_id=training.id)

    return render(request, 'trainings/attendance_form.html', {
        'training': training,
        'enrollments': enrollments,
        'staff': request.user,
    })


# trainings/views.py

@login_required
def training_attendance_summary(request, training_id):
    training = get_object_or_404(Training, id=training_id)

    # ✅ Allow admin, creator, or coordinator to view summary
    if not (request.user.is_superuser or request.user == training.created_by or request.user == training.coordinator):
        messages.error(request, "You are not authorized to view this attendance summary.")
        return redirect('dashboard')

    enrollments = Enrollment.objects.filter(training=training)

    return render(request, 'trainings/training_attendance_summary.html', {
        'training': training,
        'enrollments': enrollments,
        'staff': request.user,
    })


from django.http import FileResponse

@login_required
def preview_concept_note(request, training_id):
    training = get_object_or_404(Training, id=training_id)

    if not training.concept_note:
        messages.error(request, "This training does not have a concept note uploaded.")
        return redirect('training_list')

    try:
        file_path = training.concept_note.path
        return FileResponse(open(file_path, 'rb'), content_type='application/pdf')
    except FileNotFoundError:
        messages.error(request, "The concept note file was not found.")
        return redirect('training_list')
    

import csv

@login_required
@admin_required
def attendee_report(request):
    trainings = Training.objects.all()
    departments = Department.objects.all()

    selected_training = request.GET.get('training')
    selected_department = request.GET.get('department')

    enrollments = Enrollment.objects.all()
    if selected_training:
        enrollments = enrollments.filter(training_id=selected_training)
    if selected_department:
        enrollments = enrollments.filter(participant__department_id=selected_department)

    if 'export' in request.GET:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="attendees_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Full Name', 'Email', 'Department', 'Training', 'Start Date', 'End Date'])

        for enrollment in enrollments:
            writer.writerow([
                enrollment.participant.full_name,
                enrollment.participant.email,
                enrollment.participant.department.name if enrollment.participant.department else '',
                enrollment.training.title,
                enrollment.training.start_date,
                enrollment.training.end_date,
            ])
        return response

    return render(request, 'trainings/admin_attendee_report.html', {
        'enrollments': enrollments,
        'trainings': trainings,
        'departments': departments,
        'selected_training': selected_training,
        'selected_department': selected_department,
        'staff': request.user,
    })


@login_required
def my_training_report(request):
    staff = request.user

    if staff.role != 'regular':
        messages.error(request, "Only regular users can view their training report.")
        return redirect('dashboard')

    trainings = Training.objects.filter(created_by=staff)
    selected_training_id = request.GET.get('training')

    enrollments = Enrollment.objects.filter(training__in=trainings)
    if selected_training_id:
        enrollments = enrollments.filter(training_id=selected_training_id)

    if 'export' in request.GET:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="my_training_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Participant Name', 'Email', 'Training', 'Start Date', 'End Date', 'Attendance Status'])

        for e in enrollments:
            writer.writerow([
                e.participant.full_name,
                e.participant.email,
                e.training.title,
                e.training.start_date,
                e.training.end_date,
                e.attendance_status
            ])
        return response

    return render(request, 'trainings/my_training_report.html', {
        'trainings': trainings,
        'enrollments': enrollments,
        'selected_training_id': selected_training_id,
        'staff': staff,
    })


def quick_invite_create(request):
    if request.method == 'POST':
        form = QuickInviteForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            training = form.cleaned_data['training']

            # ✅ Check if Participant with this email already exists
            try:
                participant = Participant.objects.get(email=email)
                messages.info(request, "Participant already exists. Enroll instead.")

                # ✅ Optional: Pass training and email to prefill later
                return redirect(f"{reverse('enrollment_create')}?email={email}&training_id={training.id}")

            except Participant.DoesNotExist:
                # ✅ Participant doesn't exist: create and invite
                participant = Participant.objects.create(
                    email=email,
                    full_name='',
                    phone='',
                    position='',
                    notes='',
                )

                # ✅ Create enrollment
                enrollment = Enrollment.objects.create(
                    training=training,
                    participant=participant,
                    enrolled_by=request.user,
                    invite_token=uuid.uuid4()
                )

                # ✅ Send invitation
                invite_link = request.build_absolute_uri(
                    reverse('enrollment_invite_form', args=[str(enrollment.invite_token)])
                )

                send_mail(
                    subject='Training Invitation - Complete Your Profile',
                    message=f"""Dear Participant,

You are invited to the training "{training.title}".
Please complete your profile using the following link:

{invite_link}

Thank you.""",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )

                messages.success(request, "Invitation email sent successfully.")
                return redirect('dashboard')

    else:
        form = QuickInviteForm()

    return render(request, 'trainings/quick_invite_form.html', {
        'form': form,
        'staff': request.user
    })



# === Enrollment Edit View ===
@login_required
def enrollment_edit(request, pk):
    enrollment = get_object_or_404(Enrollment, pk=pk)
    staff = request.user

    if staff.role != 'admin' and enrollment.enrolled_by != staff:
        messages.error(request, "You are not authorized to edit this enrollment.")
        return redirect('enrollment_list')

    if request.method == 'POST':
        form = EnrollmentForm(request.POST, instance=enrollment, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Enrollment updated successfully.")
            return redirect('enrollment_list')
        else:
            # ❗ SHOW detailed validation errors here
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")
    else:
        form = EnrollmentForm(instance=enrollment, user=request.user)

    return render(request, 'trainings/enrollment_form.html', {
        'form': form,
        'staff': staff,
        'editing': True,
        'enrollment': enrollment,
    })


# === Enrollment Delete View ===
@login_required
def enrollment_delete(request, pk):
    enrollment = get_object_or_404(Enrollment, pk=pk)
    staff = request.user

    # ✅ Permission: allow only admin or enrollment creator to delete
    if staff.role != 'admin' and enrollment.enrolled_by != staff:
        messages.error(request, "You are not authorized to delete this enrollment.")
        return redirect('enrollment_list')

    if request.method == 'POST':
        enrollment.delete()
        messages.success(request, "Enrollment deleted successfully.")
        return redirect('enrollment_list')

    return render(request, 'trainings/enrollment_confirm_delete.html', {
        'enrollment': enrollment,
        'staff': staff
    })


from django.contrib.auth import get_user_model
from django.http import HttpResponse

def create_superuser(request):
    User = get_user_model()

    if not User.objects.filter(username='elina').exists():
        user = User.objects.create_superuser(
            username='elina',
            email='nsanzabandidani@gmail.com',
            password='immocent@123A'
        )
        # 👇 Set your custom fields properly after creation
        user.active = True
        user.role = 'admin'
        user.save()
        return HttpResponse("✅ Superuser created successfully!")
    else:
        return HttpResponse("⚠️ Superuser already exists.")



from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from .models import Province, District

@user_passes_test(lambda u: u.is_superuser)  # Only superuser can trigger
def load_provinces_and_districts(request):
    Province.objects.all().delete()
    District.objects.all().delete()

    # Create Provinces
    kigali = Province.objects.create(name="Kigali")
    southern = Province.objects.create(name="Southern")
    northern = Province.objects.create(name="Northern")
    eastern = Province.objects.create(name="Eastern")
    western = Province.objects.create(name="Western")

    # Create Districts

    # Kigali
    District.objects.create(name="Gasabo", province=kigali)
    District.objects.create(name="Kicukiro", province=kigali)
    District.objects.create(name="Nyarugenge", province=kigali)

    # Southern
    District.objects.create(name="Gisagara", province=southern)
    District.objects.create(name="Huye", province=southern)
    District.objects.create(name="Kamonyi", province=southern)
    District.objects.create(name="Muhanga", province=southern)
    District.objects.create(name="Nyamagabe", province=southern)
    District.objects.create(name="Nyanza", province=southern)
    District.objects.create(name="Nyaruguru", province=southern)
    District.objects.create(name="Ruhango", province=southern)

    # Northern
    District.objects.create(name="Burera", province=northern)
    District.objects.create(name="Gakenke", province=northern)
    District.objects.create(name="Gicumbi", province=northern)
    District.objects.create(name="Musanze", province=northern)
    District.objects.create(name="Rulindo", province=northern)

    # Eastern
    District.objects.create(name="Bugesera", province=eastern)
    District.objects.create(name="Gatsibo", province=eastern)
    District.objects.create(name="Kayonza", province=eastern)
    District.objects.create(name="Kirehe", province=eastern)
    District.objects.create(name="Ngoma", province=eastern)
    District.objects.create(name="Nyagatare", province=eastern)
    District.objects.create(name="Rwamagana", province=eastern)

    # Western
    District.objects.create(name="Karongi", province=western)
    District.objects.create(name="Ngororero", province=western)
    District.objects.create(name="Nyabihu", province=western)
    District.objects.create(name="Nyamasheke", province=western)
    District.objects.create(name="Rubavu", province=western)
    District.objects.create(name="Rusizi", province=western)
    District.objects.create(name="Rutsiro", province=western)

    return HttpResponse("✅ Provinces and Districts loaded successfully!")
