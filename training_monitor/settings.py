from pathlib import Path
import os
from dotenv import load_dotenv
import dj_database_url

load_dotenv()

# === Base Directory ===
BASE_DIR = Path(__file__).resolve().parent.parent

# === Security ===
SECRET_KEY = os.environ.get('SECRET_KEY', 'insecure-key-for-dev')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'  # Default to True for dev
ALLOWED_HOSTS = ['56.228.17.149', 'localhost', '127.0.0.1']


# === Installed Apps ===
INSTALLED_APPS = [
    'dal',
    'dal_select2',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'trainings',
    'widget_tweaks',
    'storages',
]

# === Middleware ===
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# === URL and WSGI ===
ROOT_URLCONF = 'training_monitor.urls'
WSGI_APPLICATION = 'training_monitor.wsgi.application'

# === Templates ===
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]



# === Database ===
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'trainingdb',
        'USER': 'traininguser',
        'PASSWORD': 'immocent@123A',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

#DATABASES = {
   # 'default': dj_database_url.config(
   #     default=os.environ.get('postgresql://training_user:9JCRmTbANGozg0FmbALc010cDWCCMh4R@dpg-d0c8a29r0fns73e5jjmg-a/trainingdb_2lfy')
   # )
#}

AUTH_USER_MODEL = 'trainings.Staff'


# === Password Validation ===
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# === Localization ===
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# === Static Files ===
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'trainings/static']
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# === AWS S3 Media Storage ===
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'


# === Authentication ===
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# === Email Settings ===
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# === Render Deployment ===
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG



