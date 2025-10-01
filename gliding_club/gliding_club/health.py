#adding health checks for the app

from django.http import JsonResponse
from django.db import connection
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings
import os
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

def health_check(request):
    """Comprehensive health check for Gliding Club Training Records system"""
    health_status = {
        'status': 'healthy',
        'service': 'NGC Student Records Management',
        'timestamp': timezone.now().isoformat(),
        'checks': {}
    }
    
    overall_healthy = True
    
    # 1. Database connectivity and data sanity
    try:
        with connection.cursor() as cursor:
            # Check database connection
            cursor.execute("SELECT 1")
            
            # Check core tables exist and have data
            cursor.execute("SELECT COUNT(*) FROM auth_user WHERE is_active = true")
            user_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM training_records_trainingrecord")
            record_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM training_records_exercise")
            exercise_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM training_records_groundbriefingtopic")
            briefing_count = cursor.fetchone()[0]
            
        health_status['checks']['database'] = {
            'status': 'healthy',
            'connection': 'connected',
            'users': user_count,
            'training_records': record_count,
            'exercises': exercise_count,
            'ground_briefings': briefing_count
        }
    except Exception as e:
        health_status['checks']['database'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        overall_healthy = False
    
    # 2. Email service configuration (AWS SES)
    try:
        email_backend = getattr(settings, 'EMAIL_BACKEND', 'not-configured')
        aws_region = getattr(settings, 'AWS_SES_REGION_NAME', 'not-set')
        aws_key = getattr(settings, 'AWS_ACCESS_KEY_ID', '')
        
        # Mask the access key for security
        masked_key = aws_key[:8] + "***" if aws_key else "not-set"
        
        health_status['checks']['email'] = {
            'status': 'configured',
            'backend': email_backend,
            'region': aws_region,
            'access_key': masked_key,
            'ses_configured': 'django_ses' in email_backend
        }
    except Exception as e:
        health_status['checks']['email'] = {
            'status': 'error',
            'error': str(e)
        }
    
    # 3. File system and logging
    try:
        log_checks = []
        log_files = ['/app/logs/django.log', '/app/logs/notifications.log', '/app/logs/commands.log']
        
        for log_file in log_files:
            log_dir = os.path.dirname(log_file)
            exists = os.path.exists(log_dir)
            writable = os.access(log_dir, os.W_OK) if exists else False
            
            log_checks.append({
                'file': os.path.basename(log_file),
                'directory_exists': exists,
                'writable': writable
            })
        
        # Check media/static directories
        media_writable = os.path.exists('/app/media') and os.access('/app/media', os.W_OK)
        static_exists = os.path.exists('/app/staticfiles')
        
        health_status['checks']['filesystem'] = {
            'status': 'healthy',
            'log_files': log_checks,
            'media_writable': media_writable,
            'static_exists': static_exists
        }
    except Exception as e:
        health_status['checks']['filesystem'] = {
            'status': 'error',
            'error': str(e)
        }
    
    # 4. Authentication system (AllAuth + Social)
    try:
        # Check if social authentication is configured
        social_providers = getattr(settings, 'SOCIALACCOUNT_PROVIDERS', {})
        google_configured = bool(social_providers.get('google', {}).get('APP', {}).get('client_id'))
        microsoft_configured = bool(social_providers.get('microsoft', {}).get('APP', {}).get('client_id'))
        
        health_status['checks']['authentication'] = {
            'status': 'configured',
            'allauth_installed': 'allauth' in settings.INSTALLED_APPS,
            'social_providers': {
                'google': google_configured,
                'microsoft': microsoft_configured
            }
        }
    except Exception as e:
        health_status['checks']['authentication'] = {
            'status': 'error',
            'error': str(e)
        }
    
    # 5. Internationalization (Hebrew/English support)
    try:
        languages = getattr(settings, 'LANGUAGES', [])
        locale_paths = getattr(settings, 'LOCALE_PATHS', [])
        
        # Check if Hebrew locale files exist
        hebrew_po_exists = False
        hebrew_mo_exists = False
        for locale_path in locale_paths:
            hebrew_po = os.path.join(locale_path, 'he', 'LC_MESSAGES', 'django.po')
            hebrew_mo = os.path.join(locale_path, 'he', 'LC_MESSAGES', 'django.mo')
            if os.path.exists(hebrew_po):
                hebrew_po_exists = True
            if os.path.exists(hebrew_mo):
                hebrew_mo_exists = True
        
        health_status['checks']['internationalization'] = {
            'status': 'configured',
            'languages': [code for code, name in languages],
            'hebrew_translations': {
                'po_file': hebrew_po_exists,
                'mo_file': hebrew_mo_exists
            }
        }
    except Exception as e:
        health_status['checks']['internationalization'] = {
            'status': 'error',
            'error': str(e)
        }
    
    # 6. Security settings
    try:
        security_checks = {
            'debug_mode': settings.DEBUG,
            'secret_key_set': bool(settings.SECRET_KEY and settings.SECRET_KEY != 'fallback-key-for-development-only'),
            'allowed_hosts_configured': bool(settings.ALLOWED_HOSTS and settings.ALLOWED_HOSTS != ['*']),
            'csp_enabled': 'csp' in settings.INSTALLED_APPS,
            'axes_enabled': 'axes' in settings.INSTALLED_APPS  # Login attempt limiting
        }
        
        health_status['checks']['security'] = {
            'status': 'configured',
            **security_checks
        }
    except Exception as e:
        health_status['checks']['security'] = {
            'status': 'error',
            'error': str(e)
        }
    
    # Set overall status
    if not overall_healthy:
        health_status['status'] = 'unhealthy'
    
    # Log health check
    logger.info(f"Health check completed: {health_status['status']}")
    
    # Return appropriate HTTP status
    status_code = 200 if health_status['status'] == 'healthy' else 503
    
    return JsonResponse(health_status, status=status_code)

def ready_check(request):
    """Simple readiness check for load balancers"""
    try:
        # Quick database ping
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({
            'status': 'ready',
            'service': 'NGC Student Records Management'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'not ready',
            'error': str(e)
        }, status=503)