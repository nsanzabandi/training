# trainings/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid
from django.core.validators import RegexValidator

# === Province and District ===

class Province(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class District(models.Model):
    name = models.CharField(max_length=100)
    province = models.ForeignKey(Province, on_delete=models.CASCADE, related_name='districts')

    class Meta:
        unique_together = ('name', 'province')
        ordering = ['province', 'name']

    def __str__(self):
        return f"{self.name} ({self.province.name})"

# === Department ===

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

# === Custom User: Staff ===

class Staff(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('regular', 'Regular'),
        ('supervisor', 'Supervisor'),
    )

    contact_number = models.CharField(max_length=20, blank=True)
    position = models.CharField(max_length=100, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username} ({self.role})"

# === Training ===

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
    province = models.ForeignKey(Province, on_delete=models.SET_NULL, null=True, blank=True)
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True)
    venue = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    max_capacity = models.PositiveIntegerField()
    rejection_reason = models.TextField(blank=True, null=True)

    coordinator = models.ForeignKey(
        'Staff',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='coordinated_trainings'
    )
    created_by = models.ForeignKey('Staff', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

# === Training Document ===

class TrainingDocument(models.Model):
    training = models.ForeignKey(Training, related_name='documents', on_delete=models.CASCADE)
    file = models.FileField(upload_to='training_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name

# === Participant ===

class Participant(models.Model):
    national_id = models.CharField(
        primary_key=True,
        max_length=16,
        validators=[
            RegexValidator(
                regex=r'^[0-9]{1,16}$|^[a-zA-Z0-9]{1,50}$',
                message="Enter a valid National ID or Staff ID."
            )
        ],
        verbose_name="National ID"
    )
    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    position = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='participant_photos/', null=True, blank=True)

    class Meta:
        ordering = ['full_name']

    def __str__(self):
        return self.full_name

# === Enrollment ===

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
    participant = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        to_field='national_id',
        db_column='participant_id'
    )
    enrollment_date = models.DateTimeField(auto_now_add=True)
    enrolled_by = models.ForeignKey('Staff', on_delete=models.SET_NULL, null=True)
    confirmation_status = models.CharField(max_length=10, choices=CONFIRMATION_CHOICES, default='pending')
    confirmation_date = models.DateTimeField(null=True, blank=True)
    attendance_status = models.CharField(max_length=15, choices=ATTENDANCE_CHOICES, default='not_marked')
    notes = models.TextField(blank=True)
    invite_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        ordering = ['-enrollment_date']

    def __str__(self):
        return f"{self.participant.full_name} in {self.training.title}"
