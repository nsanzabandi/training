from django.contrib.auth.models import User
from django.db import models
import uuid

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Staff(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('regular', 'Regular'),
        ('supervisor', 'Supervisor'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, null=True, blank=True)
    active = models.BooleanField(default=False)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    contact_number = models.CharField(max_length=20, blank=True)
    position = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"



class Training(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
    )

    title = models.CharField(max_length=200)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField()
    location = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    max_capacity = models.PositiveIntegerField()

    coordinator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='coordinated_trainings'
    )

    category = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    concept_note = models.FileField(upload_to='concept_notes/', null=True, blank=True)

    def __str__(self):
        return self.title



class Participant(models.Model):
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    position = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='participant_photos/', null=True, blank=True)

    def __str__(self):
        return self.full_name


class Enrollment(models.Model):
    CONFIRMATION_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('declined', 'Declined'),
    )

    ATTENDANCE_CHOICES = (
        ('not_marked', 'Not Marked'),
        ('attended', 'Attended'),
        ('absent', 'Absent'),
    )

    training = models.ForeignKey(Training, on_delete=models.CASCADE)
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE)
    enrollment_date = models.DateTimeField(auto_now_add=True)
    enrolled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    confirmation_status = models.CharField(max_length=10, choices=CONFIRMATION_CHOICES, default='pending')
    confirmation_date = models.DateTimeField(null=True, blank=True)
    attendance_status = models.CharField(max_length=15, choices=ATTENDANCE_CHOICES, default='not_marked')
    notes = models.TextField(blank=True)
    invite_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def __str__(self):
        return f"{self.participant.full_name} in {self.training.title}"
