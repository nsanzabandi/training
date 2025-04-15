# === Imports ===
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.timezone import now
from django.http import HttpResponse, FileResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import get_template
from django.conf import settings
from django.db import IntegrityError
from django.db.models import Q

import io, os, csv, qrcode
from collections import defaultdict
from xhtml2pdf import pisa

# === App Imports ===
from .models import Staff, Training, Participant, Department, Enrollment
from .forms import UserUpdateForm, TrainingForm, ParticipantForm, DepartmentForm, StaffForm, EnrollmentForm, UserSignupForm
from .utils import admin_required, get_staff_for_user

# === Dashboard Views ===
@login_required
def dashboard(request):
    try:
        staff = request.user.staff
        if not staff.active or not staff.role:
            return redirect('pending_approval')
    except Staff.DoesNotExist:
        staff = Staff.objects.create(
            user=request.user,
            role='admin' if request.user.is_superuser else 'regular',
            department='General'
        )

    if staff.role == 'admin':
        trainings = Training.objects.all()
    elif staff.role == 'supervisor':
        trainings = Training.objects.filter(coordinator=request.user)
    else:
        trainings = Training.objects.filter(department=staff.department)

    enrollments = Enrollment.objects.filter(training__in=trainings)
    participants = Participant.objects.all()
    if staff.role == 'regular':
        participants = participants.filter(department=staff.department)

    training_stats = {}
    for training in trainings:
        confirmed = training.enrollment_set.filter(confirmation_status='confirmed').count()
        pending = training.enrollment_set.filter(confirmation_status='pending').count()
        training_stats[training.id] = {
            'confirmed': confirmed,
            'pending': pending,
            'total': training.enrollment_set.count(),
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
    staff = request.user.staff
    trainings = Training.objects.filter(coordinator=request.user)
    enrollments = Enrollment.objects.filter(training__in=trainings)
    total_participants = enrollments.values('participant').distinct().count()
    total_confirmed = enrollments.filter(confirmation_status='confirmed').count()

    context = {
        'staff': staff,
        'trainings': trainings,
        'total_trainings': trainings.count(),
        'total_participants': total_participants,
        'total_confirmed': total_confirmed,
    }

    return render(request, 'trainings/supervisor_dashboard.html', context)

# === Training Views ===
@login_required
def training_list(request):
    staff = request.user.staff
    query = request.GET.get('q')
    if staff.role == 'admin':
        trainings = Training.objects.all()
    elif staff.role == 'regular':
        trainings = Training.objects.filter(department=staff.department)
    else:
        trainings = Training.objects.filter(created_by=request.user)

    if query:
        trainings = trainings.filter(
            Q(title__icontains=query) |
            Q(department__name__icontains=query)
        )

    return render(request, 'trainings/training_list.html', {
        'trainings': trainings,
        'staff': staff
    })

@login_required
def training_create(request):
    staff = request.user.staff
    if request.method == 'POST':
        form = TrainingForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            training = form.save(commit=False)
            training.created_by = request.user
            if staff.role == 'regular':
                training.department = staff.department
            training.save()
            messages.success(request, "Training created successfully.")
            return redirect('training_list')
    else:
        form = TrainingForm(user=request.user)
        if staff.role == 'regular':
            form.fields['department'].queryset = Department.objects.filter(id=staff.department.id)
            form.fields['department'].initial = staff.department
            form.fields['department'].widget.attrs['readonly'] = True

    return render(request, 'trainings/training_form.html', {'form': form, 'staff': staff})

@login_required
def training_edit(request, pk):
    training = get_object_or_404(Training, pk=pk)
    if request.user != training.created_by and not request.user.is_staff:
        return redirect('training_list')
    if request.method == 'POST':
        form = TrainingForm(request.POST, instance=training)
        if form.is_valid():
            form.save()
            return redirect('training_list')
    else:
        form = TrainingForm(instance=training)
    return render(request, 'trainings/training_form.html', {'form': form, 'staff': request.user.staff})

@login_required
def training_delete(request, pk):
    training = get_object_or_404(Training, pk=pk)
    if request.user == training.created_by or request.user.is_staff:
        training.delete()
    return redirect('training_list')

@login_required
def approve_training(request, training_id):
    training = get_object_or_404(Training, id=training_id)
    if request.user.staff.role == 'admin':
        training.status = 'approved'
        training.save()
    return redirect('dashboard')

@login_required
def reject_training(request, training_id):
    training = get_object_or_404(Training, id=training_id)
    if request.user.staff.role == 'admin':
        training.status = 'rejected'
        training.save()
    return redirect('dashboard')

@login_required
def mark_attendance(request, training_id):
    training = get_object_or_404(Training, id=training_id)

    if training.status != 'approved':
        messages.error(request, "Attendance cannot be marked until this training is approved.")
        return redirect('dashboard')

    if not (
        request.user.is_staff or
        training.created_by == request.user or
        training.coordinator == request.user
    ):
        messages.error(request, "You are not allowed to mark attendance for this training.")
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
        'staff': request.user.staff
    })

@login_required
def training_attendance_summary(request, training_id):
    training = get_object_or_404(Training, id=training_id)

    if not (
        request.user.is_staff or
        training.created_by == request.user or
        training.coordinator == request.user
    ):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('dashboard')

    enrollments = Enrollment.objects.filter(training=training)

    return render(request, 'trainings/training_attendance_summary.html', {
        'training': training,
        'enrollments': enrollments,
    })

# === Participant Views ===
@login_required
def participant_list(request):
    staff = request.user.staff
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
    try:
        staff = request.user.staff
    except Staff.DoesNotExist:
        staff = None

    if request.method == 'POST':
        form = ParticipantForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Participant created successfully.")
            return redirect('participant_list')
    else:
        form = ParticipantForm(user=request.user)

    return render(request, 'trainings/participant_form.html', {
        'form': form,
        'staff': staff
    })

@login_required
def participant_edit(request, pk):
    participant = get_object_or_404(Participant, pk=pk)
    staff = request.user.staff

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
        form = ParticipantForm(instance=participant, user=request.user)

    return render(request, 'trainings/participant_form.html', {
        'form': form,
        'staff': staff
    })

@login_required
def participant_delete(request, pk):
    participant = get_object_or_404(Participant, pk=pk)
    staff = request.user.staff

    if staff.role == 'regular' and participant.department != staff.department:
        messages.error(request, "You are not allowed to delete this participant.")
        return redirect('participant_list')

    participant.delete()
    return redirect('participant_list')

@login_required
def participant_detail(request, participant_id):
    participant = get_object_or_404(Participant, id=participant_id)
    enrollments = Enrollment.objects.filter(participant=participant)
    return render(request, 'trainings/participant_detail.html', {
        'participant': participant,
        'enrollments': enrollments
    })

@login_required
def participant_pdf_report(request, participant_id):
    participant = get_object_or_404(Participant, id=participant_id)
    enrollments = Enrollment.objects.filter(participant=participant)

    from datetime import datetime
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
    query = request.GET.get('q')
    enrollments = Enrollment.objects.all()
    if query:
        enrollments = enrollments.filter(
            Q(participant__full_name__icontains=query) |
            Q(training__title__icontains=query)
        )
    staff = get_staff_for_user(request.user)
    return render(request, 'trainings/enrollment_list.html', {
        'enrollments': enrollments,
        'staff': staff
    })

@login_required
def enrollment_create(request):
    try:
        staff = request.user.staff
    except Staff.DoesNotExist:
        staff = None

    if request.method == 'POST':
        form = EnrollmentForm(request.POST, user=request.user)
        if form.is_valid():
            enrollment = form.save(commit=False)
            enrollment.enrolled_by = request.user
            if enrollment.confirmation_status == 'confirmed':
                enrollment.confirmation_date = now()
            enrollment.save()

            confirm_url = request.build_absolute_uri(
                reverse('confirm_enrollment', args=[str(enrollment.invite_token)])
            )

            send_mail(
                subject='Training Confirmation',
                message=f"""Dear {enrollment.participant.full_name},

Please confirm your attendance for '{enrollment.training.title}' by clicking the link below:
{confirm_url}""",
                from_email='noreply@yourdomain.com',
                recipient_list=[enrollment.participant.email],
                fail_silently=False,
            )

            messages.success(request, 'Enrollment created and confirmation email sent.')
            return redirect('enrollment_list')
    else:
        form = EnrollmentForm(user=request.user)

    return render(request, 'trainings/enrollment_form.html', {
        'form': form,
        'staff': staff
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

# === Department Views ===
@login_required
@admin_required
def department_list(request):
    query = request.GET.get('q')
    departments = Department.objects.all()
    if query:
        departments = departments.filter(name__icontains=query)
    return render(request, 'trainings/department_list.html', {
        'departments': departments,
        'staff': request.user.staff
    })

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
    return render(request, 'trainings/department_form.html', {
        'form': form,
        'staff': request.user.staff
    })

@login_required
@admin_required
def department_edit(request, pk):
    staff = request.user.staff
    department = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            return redirect('department_list')
    else:
        form = DepartmentForm(instance=department)
    return render(request, 'trainings/department_form.html', {
        'form': form,
        'staff': staff
    })

@login_required
@admin_required
def department_delete(request, pk):
    department = get_object_or_404(Department, pk=pk)
    department.delete()
    return redirect('department_list')

# === Staff Views ===

@login_required
@admin_required
def staff_delete(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    user = staff.user
    staff.delete()
    user.delete()
    messages.success(request, "Staff member deleted successfully.")
    return redirect('staff_list')

@login_required
@admin_required
def approve_staff(request, staff_id):
    staff = get_object_or_404(Staff, pk=staff_id)
    staff.active = True
    staff.save()
    staff.user.is_active = True  # ✅ Allow login
    staff.user.save()
    messages.success(request, f"{staff.user.get_full_name()} has been approved and activated.")
    return redirect('staff_list')
@login_required
@admin_required
def staff_list(request):
    if request.user.staff.role != 'admin':
        return redirect('dashboard')

    query = request.GET.get('q')
    staff_members = Staff.objects.all()
    if query:
        staff_members = staff_members.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(department__name__icontains=query) |
            Q(role__icontains=query)
        )
    return render(request, 'trainings/staff_list.html', {
        'staff_members': staff_members,
        'staff': request.user.staff
    })

@login_required
@admin_required
def staff_create(request):
    if request.user.staff.role != 'admin':
        return redirect('dashboard')

    if request.method == 'POST':
        user_form = UserCreationForm(request.POST)
        staff_form = StaffForm(request.POST)

        if user_form.is_valid() and staff_form.is_valid():
            user = user_form.save()
            staff = user.staff
            staff.role = staff_form.cleaned_data['role']
            staff.department = staff_form.cleaned_data['department']
            staff.contact_number = staff_form.cleaned_data['contact_number']
            staff.position = staff_form.cleaned_data['position']
            staff.active = staff_form.cleaned_data['active']
            staff.save()
            return redirect('staff_list')
    else:
        user_form = UserCreationForm()
        staff_form = StaffForm()

    return render(request, 'trainings/staff_form.html', {
        'user_form': user_form,
        'staff_form': staff_form,
        'staff': request.user.staff
    })

@login_required
@admin_required
def staff_edit(request, pk):
    if request.user.staff.role != 'admin':
        return redirect('dashboard')

    staff = get_object_or_404(Staff, pk=pk)
    user = staff.user

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=user)
        staff_form = StaffForm(request.POST, instance=staff)
        if user_form.is_valid() and staff_form.is_valid():
            user_form.save()
            staff_form.save()
            return redirect('staff_list')
    else:
        user_form = UserUpdateForm(instance=user)
        staff_form = StaffForm(instance=staff)

    return render(request, 'trainings/staff_form.html', {
        'user_form': user_form,
        'staff_form': staff_form,
        'editing': True,
        'staff_id': staff.id,
    })

@login_required
def pending_staff_list(request):
    if not request.user.is_superuser:
        return redirect('dashboard')

    pending_staff = Staff.objects.filter(active=False)
    return render(request, 'trainings/pending_staff_list.html', {
        'pending_staff': pending_staff,
        'staff': request.user.staff
    })

@login_required
@admin_required
def approve_staff(request, staff_id):
    staff = get_object_or_404(Staff, pk=staff_id)
    if request.method == 'POST':
        form = StaffForm(request.POST, instance=staff)
        if form.is_valid():
            staff = form.save(commit=False)
            staff.active = True
            staff.user.is_active = True
            staff.user.save()
            staff.save()
            messages.success(request, f"{staff.user.get_full_name()} has been approved and activated.")
            return redirect('staff_list')
    else:
        form = StaffForm(instance=staff)

    return render(request, 'trainings/approve_staff_form.html', {
        'form': form,
        'staff_obj': staff,
        'staff': request.user.staff
    })

# === Report Views ===
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

        for e in enrollments:
            writer.writerow([
                e.participant.full_name,
                e.participant.email,
                e.participant.department,
                e.training.title,
                e.training.start_date,
                e.training.end_date,
            ])
        return response

    return render(request, 'trainings/admin_attendee_report.html', {
        'enrollments': enrollments,
        'trainings': trainings,
        'departments': departments,
        'selected_training': selected_training,
        'selected_department': selected_department,
        'staff': request.user.staff
    })

@login_required
def my_training_report(request):
    staff = request.user.staff

    if staff.role != 'regular':
        return redirect('dashboard')

    trainings = Training.objects.filter(created_by=request.user)
    selected_training_id = request.GET.get('training')

    enrollments = Enrollment.objects.filter(training__in=trainings)
    if selected_training_id:
        enrollments = enrollments.filter(training_id=selected_training_id)

    if 'export' in request.GET:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="my_training_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Participant', 'Email', 'Training', 'Start Date', 'End Date', 'Attendance'])

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
        'staff': staff
    })

@admin_required
def preview_concept_note(request, training_id):
    try:
        training = Training.objects.get(id=training_id)
        file_path = training.concept_note.path

        if not os.path.exists(file_path):
            raise Http404("File does not exist.")

        return FileResponse(open(file_path, 'rb'), content_type='application/pdf')

    except Training.DoesNotExist:
        raise Http404("Training not found.")

# === Auth Views ===
def register(request):
    if request.method == 'POST':
        form = UserSignupForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password'])
                user.is_active = False  # ✅ Prevent login until approved
                user.save()

                if not hasattr(user, 'staff'):
                    Staff.objects.create(
                        user=user,
                        department=form.cleaned_data['department'],
                        role=None,  # ⛔ No role assigned until approval
                        profile_picture=form.cleaned_data.get('profile_picture'),
                        active=False
                    )

                messages.success(request, "Account created successfully. Please wait for admin approval.")
                return redirect('login')
            except IntegrityError:
                form.add_error(None, "An account with this user already exists.")
    else:
        form = UserSignupForm()
    return render(request, 'trainings/register.html', {'form': form})

@login_required
def custom_logout(request):
    logout(request)
    return redirect('login')


def pending_approval(request):
    return render(request, 'trainings/pending_approval.html')
