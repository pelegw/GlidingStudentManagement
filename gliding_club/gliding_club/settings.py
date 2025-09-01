# gliding_club/settings.py

import os
from pathlib import Path
#import django_csp

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-key-for-development-only')


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False  # Set to False in production

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
    'django.contrib.sites',
    # Third-party apps
    'csp',  # Content Security Policy
    'axes',        # Login attempt security
    
     # allauth apps
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',  # support only google and facebook for now
    'allauth.socialaccount.providers.microsoft',
    # Add more providers as needed

    # Local apps
    'training_records',
]
SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'training_records.middleware.CSPNonceMiddleware',
    'csp.middleware.CSPMiddleware',
    'training_records.middleware.FirstLoginMiddleware',  # Custom middleware for first login redirect
    'training_records.middleware.AuditLogMiddleware',  # Custom middleware for audit logging
    'axes.middleware.AxesMiddleware',  # Should be the last middleware
]
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'training_records': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
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
                'training_records.context_processors.csp_nonce',
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
        'CONN_MAX_AGE': 300,  # Keep connections alive for 60 seconds
        'OPTIONS': {
            'connect_timeout': 10,
            'sslmode': 'prefer',  # Add SSL preference
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
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
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
# Content Security Policy with nonce support
# Update CSP settings (around line 219-226)
CSP_DEFAULT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'nonce-%(csp_nonce)s'", "cdn.jsdelivr.net", "fonts.googleapis.com")
CSP_SCRIPT_SRC = ("'self'", "'nonce-%(csp_nonce)s'", "cdn.jsdelivr.net")
CSP_FONT_SRC = ("'self'", "fonts.gstatic.com", "cdn.jsdelivr.net")
CSP_IMG_SRC = ("'self'", "data:", "*.googleusercontent.com", "*.live.com", "*.microsoft.com")
CSP_CONNECT_SRC = ("'self'", "*.google.com", "*.googleapis.com", "*.microsoftonline.com", "*.live.com")

# Enable nonces for scripts and styles (important!)
CSP_INCLUDE_NONCE_IN = ['script-src', 'style-src']

# If you want to temporarily disable CSP while debugging, uncomment this line:
# CSP_REPORT_ONLY = True

# Django Axes Configuration
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesBackend',
    'training_records.auth_backends.CaseInsensitiveModelBackend',
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]
AXES_FAILURE_LIMIT = 10  # Number of login attempts before lockout
AXES_COOLOFF_TIME = 1  # Cooloff period in hours
AXES_LOCKOUT_PARAMETERS = [
    ['username'],  # Lock by username only (ignores IP)
]

AXES_PROXY_COUNT = 1
AXES_META_PRECEDENCE_ORDER = [
    'HTTP_CF_CONNECTING_IP',    # Cloudflare real IP
    'HTTP_X_FORWARDED_FOR',     # Standard proxy header
    'HTTP_X_REAL_IP',           # Nginx real IP
    'REMOTE_ADDR',              # Direct connection
]
AXES_RESET_ON_SUCCESS = True


#AllAuth Configs
ACCOUNT_LOGIN_METHODS = {'email', 'username'}  # Modern replacement
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_SESSION_REMEMBER = True
SOCIALACCOUNT_AUTO_SIGNUP = False  # Prevent automatic account creation
ACCOUNT_ADAPTER = 'training_records.adapters.NoNewUsersAdapter'  # Custom adapter
SOCIALACCOUNT_ADAPTER = 'training_records.adapters.ExistingUsersOnlySocialAdapter'
SOCIALACCOUNT_LOGIN_ON_GET = True  # Allow login via GET request
SOCIALACCOUNT_STORE_TOKENS = False  # Don't store tokens (as requested)
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': os.environ.get('GOOGLE_OAUTH2_CLIENT_ID'),
            'secret': os.environ.get('GOOGLE_OAUTH2_SECRET'),
            'key': ''
        },
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'OAUTH_PKCE_ENABLED': True,
    },
    'microsoft': {
    'APP': {
        'client_id': os.environ.get('MICROSOFT_CLIENT_ID'),
        'secret': os.environ.get('MICROSOFT_CLIENT_SECRET'),
        'key': ''
    },
    'SCOPE': [
        'openid',
        'email',
        'profile',
        'User.Read',
    ],
    'AUTH_PARAMS': {
        'prompt': 'select_account',
        'response_type': 'code',
    },
    'TENANT': os.environ.get('MICROSOFT_TENANT', 'common'),  # Add tenant
},
}