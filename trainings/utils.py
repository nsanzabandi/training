# trainings/utils.py
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Count, Q
from datetime import date
from .models import Staff, Training, Participant
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def get_staff_for_user(user):
    """Retrieve staff object for the given user, if it exists."""
    return Staff.objects.filter(user=user).first()

def check_admin_or_creator_permission(user, staff=None):
    """Check if the user is an admin or an approved creator."""
    if user.is_staff:
        return True
    return staff and staff.role == 'creator' and staff.is_approved

def check_admin_permission(user):
    """Check if the user is an admin."""
    return user.is_staff

def get_training_stats():
    """Calculate common training statistics."""
    total_trainings = Training.objects.count()
    total_participants = Participant.objects.count()
    total_attendance = Attendance.objects.filter(attended=True).count()
    participants_with_training = Participant.objects.annotate(
        training_count=Count('attendances', filter=Q(attendances__attended=True))
    ).filter(training_count__gt=0).count()
    attendance_percentage = (participants_with_training / total_participants * 100) if total_participants > 0 else 0
    return {
        'total_trainings': total_trainings,
        'total_participants': total_participants,
        'total_attendance': total_attendance,
        'attendance_percentage': round(attendance_percentage, 2),
    }

def filter_trainings_by_date(request):
    """Filter trainings based on date range from request."""
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    trainings = Training.objects.filter(start_date__gte=date.today())
    if date_from and date_to:
        trainings = trainings.filter(start_date__range=[date_from, date_to])
    return trainings

def redirect_with_error(request, message, redirect_to='trainings:dashboard'):
    """Redirect with an error message."""
    messages.error(request, message)
    return redirect(redirect_to)

def get_or_create_participant(user=None, full_name=None, email=None, phone=None, is_external=False):
    """Get or create a Participant object."""
    if user:
        staff = get_staff_for_user(user)
        if staff and staff.participant:
            return staff.participant
        elif staff:
            participant, _ = Participant.objects.get_or_create(
                full_name=f"{staff.first_name} {staff.last_name}",
                email=staff.email,
                defaults={'is_external': False}
            )
            staff.participant = participant
            staff.save()
            return participant
    else:
        if not full_name:
            raise ValueError("Full name is required for participants.")
        participant, _ = Participant.objects.get_or_create(
            email=email if email else None,
            defaults={
                'full_name': full_name,
                'phone': phone,
                'is_external': is_external
            }
        )
        return participant


def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, 'staff') or request.user.staff.role != 'admin':
            messages.error(request, "You do not have permission to access this page.")
            return redirect('dashboard')  # or redirect to a custom 'unauthorized' page
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def get_staff_for_user(user):
    try:
        return user.staff
    except Staff.DoesNotExist:
        return None


from django.shortcuts import redirect
from functools import wraps

def approved_user_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        try:
            staff = request.user.staff
            if not staff.active or not staff.role:
                return redirect('pending_approval')
        except:
            return redirect('pending_approval')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
