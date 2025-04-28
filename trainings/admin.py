# trainings/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Staff, Department, Province, District,
    Training, Participant, Enrollment, TrainingDocument
)

# === Staff Admin ===
@admin.register(Staff)
class StaffAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (None, {
            'fields': ('role', 'department', 'contact_number', 'position', 'profile_picture', 'active')
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {
            'fields': ('role', 'department', 'contact_number', 'position', 'profile_picture', 'active')
        }),
    )
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'department', 'active']
    list_filter = ['role', 'department', 'active']

    def save_model(self, request, obj, form, change):
        """Auto-set active=True and role if missing when creating staff."""
        if not change:  # Only when creating, not editing
            if obj.active is None:
                obj.active = True
            if not obj.role:
                obj.role = 'regular'  # Default to regular if no role provided
        super().save_model(request, obj, form, change)


# === Department Admin ===

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

# === Province Admin ===

@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

# === District Admin ===

@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ['name', 'province']
    list_filter = ['province']
    search_fields = ['name']

# === Training Admin ===

@admin.register(Training)
class TrainingAdmin(admin.ModelAdmin):
    list_display = ['title', 'start_date', 'end_date', 'department', 'province', 'district', 'status']
    list_filter = ['status', 'department', 'province', 'district']
    search_fields = ['title', 'venue']

# === Participant Admin ===

@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'phone', 'department', 'position']
    list_filter = ['department']
    search_fields = ['full_name', 'email', 'phone']

# === Enrollment Admin ===

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['participant', 'training', 'confirmation_status', 'attendance_status', 'enrollment_date']
    list_filter = ['confirmation_status', 'attendance_status']
    search_fields = ['participant__full_name', 'training__title']

# === Training Document Admin ===

@admin.register(TrainingDocument)
class TrainingDocumentAdmin(admin.ModelAdmin):
    list_display = ['file', 'training', 'uploaded_at']
    list_filter = ['uploaded_at']
