# trainings/urls.py
from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    # === Dashboard and Authentication ===
    path('', views.dashboard, name='dashboard'),
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='custom_logout'),
    path('register/', views.register, name='register'),
    path('pending-approval/', views.pending_approval, name='pending_approval'),

    # === Trainings ===
    path('trainings/', views.training_list, name='training_list'),
    path('trainings/new/', views.training_create, name='training_create'),
    path('trainings/edit/<int:pk>/', views.training_edit, name='training_edit'),
    path('trainings/delete/<int:pk>/', views.training_delete, name='training_delete'),
    path('trainings/<int:training_id>/attendance/', views.mark_attendance, name='mark_attendance'),
    path('trainings/approve/<int:training_id>/', views.approve_training, name='approve_training'),
    path('trainings/reject/<int:training_id>/', views.reject_training, name='reject_training'),
    path('trainings/<int:training_id>/attendance/summary/', views.training_attendance_summary, name='training_attendance_summary'),
    path('trainings/<int:training_id>/reject-with-reason/', views.reject_training_with_reason, name='reject_training_with_reason'),
    path('trainings/document/delete/<int:doc_id>/', views.delete_training_document, name='delete_training_document'),
    path('preview-concept-note/<int:training_id>/', views.preview_concept_note, name='preview_concept_note'),

    # === Participants ===
    path('participants/', views.participant_list, name='participant_list'),
    path('participants/new/', views.participant_create, name='participant_create'),
    path('participants/edit/<str:pk>/', views.participant_edit, name='participant_edit'),
    path('participants/delete/<str:pk>/', views.participant_delete, name='participant_delete'),
    path('participants/<str:participant_id>/detail/', views.participant_detail, name='participant_detail'),
    path('participants/<str:participant_id>/report/pdf/', views.participant_pdf_report, name='participant_pdf_report'),

    # === Departments ===
    path('departments/', views.department_list, name='department_list'),
    path('departments/new/', views.department_create, name='department_create'),
    path('departments/edit/<int:pk>/', views.department_edit, name='department_edit'),
    path('departments/delete/<int:pk>/', views.department_delete, name='department_delete'),

    # === Staff ===
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/new/', views.staff_create, name='staff_create'),
    path('staff/edit/<int:pk>/', views.staff_edit, name='staff_edit'),
    path('staff/<int:staff_id>/approve/', views.approve_staff, name='approve_staff'),
    path('staff/<int:pk>/delete/', views.staff_delete, name='staff_delete'),

    # === Enrollment ===
    path('enrollments/', views.enrollment_list, name='enrollment_list'),
    path('enrollments/new/', views.enrollment_create, name='enrollment_create'),
    path('confirm/<uuid:token>/', views.confirm_enrollment, name='confirm_enrollment'),
    path('enrollment/invite/<uuid:token>/', views.enrollment_invite_form, name='enrollment_invite_form'),
    path('enrollment/<int:pk>/edit/', views.enrollment_edit, name='enrollment_edit'),
    path('enrollment/<int:pk>/delete/', views.enrollment_delete, name='enrollment_delete'),

    # === Supervisor Dashboard ===
    path('supervisor/dashboard/', views.supervisor_dashboard, name='supervisor_dashboard'),

    # === Reports ===
    path('reports/attendees/', views.attendee_report, name='attendee_report'),
    path('reports/my-training/', views.my_training_report, name='my_training_report'),

    # === Quick Invite and Thank You Page ===
    path('invite/', views.quick_invite_create, name='quick_invite_create'),
    path('thank-you/', views.thank_you_page, name='thank_you'),

    # === AJAX APIs ===
    path('ajax/load-districts/', views.load_districts, name='ajax_load_districts'),
    path('api/participant-history/<str:national_id>/', views.participant_training_history, name='participant_training_history'),

    # === Password Reset (Django built-in views) ===
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='auth/password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='auth/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='auth/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='auth/password_reset_complete.html'), name='password_reset_complete'),
]

# Serving media files during development
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
