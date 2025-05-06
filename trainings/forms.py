# trainings/forms.py

from django import forms
from .models import Training, Participant, Department, Staff, Enrollment
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

# ✅ Correct UserUpdateForm (only one definition now)
class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

# ✅ Department Form
class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'})
        }

# ✅ Training Form
class TrainingForm(forms.ModelForm):
    class Meta:
        model = Training
        exclude = [
            'created_by', 'status', 'created_at',
            'concept_note', 'participant_list', 'agenda', 'rejection_reason',
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'venue': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter venue name (e.g., Serena Hotel)'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # ✅ Correct supervisor filtering
        self.fields['coordinator'].queryset = Staff.objects.filter(role='supervisor')

        if user and hasattr(user, 'staff') and user.staff.role == 'regular':
            self.fields['department'].queryset = Department.objects.filter(id=user.staff.department.id)
            self.fields['department'].initial = user.staff.department
            self.fields['department'].widget.attrs['readonly'] = True

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError("End date cannot be before start date.")

        return cleaned_data


# ✅ Participant Form
class ParticipantForm(forms.ModelForm):
    class Meta:
        model = Participant
        fields = ['national_id', 'email', 'full_name', 'department', 'phone', 'position', 'notes', 'profile_picture']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and hasattr(user, 'staff') and user.staff.role == 'regular':
            self.fields['department'].queryset = Department.objects.filter(id=user.staff.department.id)
            self.fields['department'].initial = user.staff.department
            self.fields['department'].widget.attrs['readonly'] = True

    def clean(self):
        cleaned_data = super().clean()
        national_id = cleaned_data.get('national_id')
        email = cleaned_data.get('email')

        if national_id:
            qs = Participant.objects.filter(national_id=national_id)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("A participant with this National ID already exists.")

        if email:
            qs = Participant.objects.filter(email=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("A participant with this Email already exists.")

        return cleaned_data

# ✅ Staff Form
class StaffSignupForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Confirm Password")

    class Meta:
        model = Staff
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'role', 'department', 'position', 'contact_number', 'profile_picture'
        ]

    def clean_username(self):
        username = self.cleaned_data.get('username')
        qs = get_user_model().objects.filter(username=username)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        qs = get_user_model().objects.filter(email=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            self.add_error('password2', "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        staff = super().save(commit=False)
        staff.set_password(self.cleaned_data['password1'])
        staff.active = False  # Adjust based on your logic
        if commit:
            staff.save()
        return staff

        

# ✅ Custom User Creation (for Django admin compatibility)
class CustomUserCreationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if "password" in field:
                self.fields[field].widget.attrs.update({'class': 'form-control'})
            else:
                self.fields[field].widget.attrs.update({'class': 'form-control'})

# ✅ Enrollment Form
class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ['participant', 'training', 'confirmation_status', 'attendance_status', 'notes']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and hasattr(user, 'staff') and user.staff.role == 'regular':
            self.fields['participant'].queryset = Participant.objects.filter(department=user.staff.department)
            self.fields['training'].queryset = Training.objects.filter(department=user.staff.department)

    def clean(self):
        cleaned_data = super().clean()
        participant = cleaned_data.get('participant')
        training = cleaned_data.get('training')

        if participant and training:
            qs = Enrollment.objects.filter(participant=participant)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.filter(training=training).exists():
                raise forms.ValidationError("❌ This participant is already enrolled in this training.")

            # ❗ Prevent overlap: cannot enroll if already enrolled in another training that overlaps
            for e in qs:
                if e.training.start_date <= training.end_date and training.start_date <= e.training.end_date:
                    raise forms.ValidationError(
                        f"❌ {participant.full_name} is already attending another training "
                        f"from {e.training.start_date} to {e.training.end_date}."
                    )

        return cleaned_data


from django.contrib.auth import get_user_model

class StaffSignupForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Confirm Password")

    class Meta:
        model = Staff
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'role', 'department', 'position', 'contact_number', 'profile_picture'
        ]

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        
        email = cleaned_data.get('email')
        if get_user_model().objects.filter(email=email).exists():
            raise forms.ValidationError("Email already exists.")

        return cleaned_data

    def save(self, commit=True):
        staff = super().save(commit=False)
        staff.set_password(self.cleaned_data['password1'])
        staff.active = False  # Adjust based on your approval logic
        if commit:
            staff.save()
        return staff

# ✅ Custom validator
def validate_national_id(value):
    if not value.isdigit():
        raise ValidationError("National ID must contain only digits.")
    if len(value) != 16:
        raise ValidationError("National ID must be exactly 16 digits long.")

# ✅ Updated form
class QuickInviteForm(forms.Form):
    national_id = forms.CharField(
        label="Participant National ID",
        max_length=16,
        required=True,
        validators=[validate_national_id],
        widget=forms.TextInput(attrs={'placeholder': 'Enter National ID'})
    )
    email = forms.EmailField(
        label="Participant Email",
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'Enter Email'})
    )
    training = forms.ModelChoiceField(
        queryset=Training.objects.filter(status='approved'),
        label="Select Approved Training",
        required=True
    )