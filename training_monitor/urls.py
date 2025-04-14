from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from trainings import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('trainings.urls')),
    path('login/', auth_views.LoginView.as_view(template_name='trainings/login.html'), name='login'),
    path('logout/', views.custom_logout, name='logout'),

]
