# trainings/admin.py
from django.contrib import admin
from .models import Participant, Staff, Training, Department

class ParticipantAdmin(admin.ModelAdmin):
    # Remove or replace 'is_external' and 'created_at' with fields that exist
    list_display = ['full_name', 'email', 'phone', 'department']  # Adjust according to your model
    list_filter = ['department']  # Remove 'is_external'

class StaffAdmin(admin.ModelAdmin):
    # Remove or replace fields that don't exist
    list_display = ['user', 'department', 'position']  # Adjust according to your model
    list_filter = ['department']  # Remove 'is_approved'

class TrainingAdmin(admin.ModelAdmin):
    # Remove or replace 'coordinator'
    list_display = ['title', 'start_date', 'end_date', 'status']  # Remove 'coordinator'


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name']


admin.site.register(Participant, ParticipantAdmin)
admin.site.register(Staff, StaffAdmin)
admin.site.register(Training, TrainingAdmin)

