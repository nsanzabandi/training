from django import forms
from .models import Training, Participant, Department,Staff, Enrollment
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'})
        }
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



class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'})
        }


class TrainingForm(forms.ModelForm):
    class Meta:
        model = Training
        fields = [
            'title', 'description', 'department', 'start_date', 'end_date',
            'start_time', 'end_time', 'location', 'max_capacity',
            'coordinator', 'concept_note'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Restrict coordinator to users whose Staff role is 'supervisor'
        supervisor_ids = Staff.objects.filter(role='supervisor').values_list('user__id', flat=True)
        self.fields['coordinator'].queryset = User.objects.filter(id__in=supervisor_ids)
        self.fields['coordinator'].required = False  # Optional, to handle cases with no supervisors
        
        if user and hasattr(user, 'staff') and user.staff.role == 'regular':
            # Restrict department to user's department
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



    
class ParticipantForm(forms.ModelForm):
    class Meta:
        model = Participant
        fields = ['full_name', 'email', 'department', 'phone', 'position']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Get the user from kwargs
        super().__init__(*args, **kwargs)
        
        if user and hasattr(user, 'staff') and user.staff.role == 'regular':
            # Restrict department dropdown to user's department only
            self.fields['department'].queryset = Department.objects.filter(id=user.staff.department.id)
            self.fields['department'].initial = user.staff.department
            self.fields['department'].widget.attrs['readonly'] = True


class StaffForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = ['role', 'department', 'contact_number', 'position', 'active']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class CustomUserCreationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if "password" in field:
                self.fields[field].widget.attrs.update({'class': 'form-control'})
            else:
                self.fields[field].widget.attrs.update({'class': 'form-control'})


class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ['participant', 'training', 'confirmation_status', 'attendance_status', 'notes']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Get the user from kwargs
        super().__init__(*args, **kwargs)
        
        if user and hasattr(user, 'staff') and user.staff.role == 'regular':
            # Restrict participant dropdown to those in the user's department
            self.fields['participant'].queryset = Participant.objects.filter(department=user.staff.department)
            # Restrict training dropdown to those in the user's department
            self.fields['training'].queryset = Training.objects.filter(department=user.staff.department)

    def clean(self):
        cleaned_data = super().clean()
        participant = cleaned_data.get('participant')
        training = cleaned_data.get('training')

        if participant and training:
            # Prevent same participant in same training
            if Enrollment.objects.filter(participant=participant, training=training).exists():
                raise forms.ValidationError("This participant is already enrolled in this training.")

            # Prevent overlapping date with other trainings
            participant_enrollments = Enrollment.objects.filter(participant=participant)
            for e in participant_enrollments:
                if e.training.start_date == training.start_date:
                    raise forms.ValidationError(
                        f"{participant.full_name} is already enrolled in another training on {training.start_date}."
                    )

        return cleaned_data



class UserSignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    department = forms.ModelChoiceField(queryset=Department.objects.all(), required=True)
    profile_picture = forms.ImageField(required=False)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'password']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm = cleaned_data.get('confirm_password')
        if password != confirm:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_active = False 
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

