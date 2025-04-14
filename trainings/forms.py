from django import forms
from .models import Training, Participant, Department,Staff, Enrollment
from django.contrib.auth.forms import UserCreationForm


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
            'coordinator', 'concept_note'  # ⬅ added field
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }


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
        fields = ['full_name', 'email', 'phone', 'department', 'position', 'notes']


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

from django import forms
from .models import Enrollment

class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ['participant', 'training', 'confirmation_status', 'attendance_status', 'notes']

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


