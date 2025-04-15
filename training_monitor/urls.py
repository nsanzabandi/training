from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from trainings import views
from trainings.views import custom_login



urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('trainings.urls')),
    path('login/', views.custom_login, name='login'), 
    path('logout/', views.custom_logout, name='logout'),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)