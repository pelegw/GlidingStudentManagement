# gliding_club/settings.py

import os
from pathlib import Path
#import django_csp

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'your-secret-key-here'  # Replace with a proper secret key in production

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = 'True'  # Set to False in production

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,*').split(',')
# Login URL
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'csp',  # Content Security Policy
    'axes',        # Login attempt security
    
    # Local apps
    'training_records',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'csp.middleware.CSPMiddleware',
    'training_records.middleware.FirstLoginMiddleware',  # Custom middleware for first login redirect
    'training_records.middleware.AuditLogMiddleware',  # Custom middleware for audit logging
    'axes.middleware.AxesMiddleware',  # Should be the last middleware
]
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'django_auth.log',
        },
    },
    'loggers': {
        'django.security.authentication': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
ROOT_URLCONF = 'gliding_club.urls'
CLUB_NAME = "NGC - Student Records Management"  # Change this to whatever name you want

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],  # Ensure this line is correct
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'training_records.context_processors.club_settings',
                'django.template.context_processors.i18n',
            ],
        },
    },
]

WSGI_APPLICATION = 'gliding_club.wsgi.application'

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'gliding_club'),
        'USER': os.environ.get('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'mysecretpassword'),
        'HOST': os.environ.get('DATABASE_HOST', 'db'),
        'PORT': os.environ.get('DATABASE_PORT', '5432'),
        'CONN_MAX_AGE': 60,  # Keep connections alive for 60 seconds
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,  # Stronger passwords
        }
    },
    #{
    #    'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    #},
    #{
    #    'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    #},
]

# Internationalization
TIME_ZONE = 'UTC'  # Update to your timezone
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Define supported languages
LANGUAGES = [
    ('en', 'English'),
    ('he', 'Hebrew'),  # Example: add French support
    # Add more languages as needed
]

# Default language
LANGUAGE_CODE = 'en'  # Default language

# Locale path where translation files will be stored
LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')


MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'training_records.User'

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# In production, add:
#SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
#SECURE_HSTS_SECONDS = 31536000  # 1 year
#SECURE_HSTS_INCLUDE_SUBDOMAINS = True
#SECURE_HSTS_PRELOAD = True

# Get CSRF trusted origins from environment variable
csrf_trusted_origins = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in csrf_trusted_origins.split(',') if origin.strip()]

# Set a default if the environment variable isn't set
if not CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS = ['https://studentlog.wasserman.me']
# Content Security Policy
CSP_DEFAULT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "cdn.jsdelivr.net", "fonts.googleapis.com")
CSP_SCRIPT_SRC = ("'self'", "cdn.jsdelivr.net")
CSP_FONT_SRC = ("'self'", "fonts.gstatic.com", "cdn.jsdelivr.net")
CSP_IMG_SRC = ("'self'", "data:")

# Django Axes Configuration
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesBackend',
    'training_records.auth_backends.CaseInsensitiveModelBackend',
    'django.contrib.auth.backends.ModelBackend',
]
AXES_FAILURE_LIMIT = 5  # Number of login attempts before lockout
AXES_LOCKOUT_PERIOD = 30  # Lockout period in minutes
AXES_COOLOFF_TIME = 1  # Cooloff period in hours