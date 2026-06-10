# training_records/middleware.py
import base64
import datetime
import json
import logging
import secrets
import threading

from django.core.serializers.json import DjangoJSONEncoder
from django.forms.models import model_to_dict
from django.shortcuts import redirect
from django.urls import reverse_lazy

logger = logging.getLogger(__name__)


class CSPNonceMiddleware:
    """
    Middleware that adds a random nonce to the request object for CSP.
    This nonce can then be used in templates and CSP headers.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Generate the nonce
        nonce = base64.b64encode(secrets.token_bytes(16)).decode('ascii')
        request.csp_nonce = nonce

        # Get the response
        response = self.get_response(request)

        # Add the nonce to CSP headers
        if 'Content-Security-Policy' in response:
            response['Content-Security-Policy'] = response['Content-Security-Policy'].replace(
                "'nonce-%(csp_nonce)s'", f"'nonce-{nonce}'"
            )

        return response


class CustomJSONEncoder(DjangoJSONEncoder):
    """Custom JSON encoder that can handle Django model objects and more"""
    def default(self, obj):
        # Handle datetime.date and datetime.datetime
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        # Handle datetime.timedelta
        elif isinstance(obj, datetime.timedelta):
            return str(obj)
        # Handle Django Model instances
        elif hasattr(obj, '_meta') and hasattr(obj, 'pk'):
            return str(obj)
        # Handle QuerySets
        elif hasattr(obj, 'model') and hasattr(obj, 'query'):
            return list(obj.values_list('pk', flat=True))
        # Handle other objects that have a string representation
        elif hasattr(obj, '__str__'):
            return str(obj)
        # Fall back to the default encoder
        return super().default(obj)


def get_model_changes(instance, created=False):
    """Get the changes made to a model instance as JSON-safe dicts.

    Old values must be captured before the row is overwritten; the pre_save
    handler stashes them on the instance as `_audit_old_values`.
    """
    old_values = {} if created else getattr(instance, '_audit_old_values', {})
    new_values = model_to_dict(instance)

    # Convert to safe JSON format
    safe_old_values = json.loads(json.dumps(old_values, cls=CustomJSONEncoder))
    safe_new_values = json.loads(json.dumps(new_values, cls=CustomJSONEncoder))

    return safe_old_values, safe_new_values


class FirstLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if user is authenticated and needs to change password
        if request.user.is_authenticated and hasattr(request.user, 'password_change_required') and request.user.password_change_required:
            # Don't redirect if already on first login page or logging out
            if request.path != reverse_lazy('first_login') and request.path != reverse_lazy('logout'):
                return redirect('first_login')

        response = self.get_response(request)
        return response


class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Expose the request to model signal handlers via thread-local storage
        # so audit entries can be attributed to the user making the change.
        current_thread = threading.current_thread()
        current_thread.request = request
        try:
            response = self.get_response(request)
        finally:
            # Clean up so a reused worker thread never sees a stale request
            if hasattr(current_thread, 'request'):
                del current_thread.request

        # We only log actions that modify data
        if request.method not in ['GET', 'HEAD', 'OPTIONS'] and request.user.is_authenticated:
            # Log the action
            try:
                if hasattr(request, 'audit_data'):
                    # Import here to avoid circular imports
                    from .models import AuditLog

                    for audit_entry in request.audit_data:
                        AuditLog.objects.create(
                            user=request.user,
                            action=audit_entry.get('action', request.method),
                            table_name=audit_entry.get('table_name', ''),
                            record_id=audit_entry.get('record_id', 0),
                            ip_address=self.get_client_ip(request),
                            user_agent=request.META.get('HTTP_USER_AGENT', ''),
                            old_values=audit_entry.get('old_values'),
                            new_values=audit_entry.get('new_values')
                        )
            except Exception:
                # Log the error but don't interrupt the response
                logger.exception("Error creating audit log")

        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# Model signal handlers for audit logging.
# These must be module-level functions: Django signals hold weak references by
# default, so locally-defined handlers are disconnected as soon as they are
# garbage collected.

def capture_old_values(sender, instance, **kwargs):
    """pre_save: capture field values before the row is overwritten"""
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._audit_old_values = model_to_dict(old_instance)
        except sender.DoesNotExist:
            instance._audit_old_values = {}
    else:
        instance._audit_old_values = {}


def training_record_audit(sender, instance, created, **kwargs):
    """post_save: queue an audit entry on the current request"""
    request = getattr(threading.current_thread(), 'request', None)
    if request is None or not hasattr(request, 'user') or not request.user.is_authenticated:
        # Saved outside an authenticated request (shell, management command):
        # skip rather than misattribute the change to another user.
        logger.warning(
            "%s %s saved outside a request context; audit entry skipped",
            instance._meta.object_name, instance.pk,
        )
        return

    old_values, new_values = get_model_changes(instance, created)

    if not hasattr(request, 'audit_data'):
        request.audit_data = []

    request.audit_data.append({
        'action': 'CREATE' if created else 'UPDATE',
        'table_name': instance._meta.db_table,
        'record_id': instance.pk,
        'old_values': old_values,
        'new_values': new_values,
    })


def setup_audit_signals():
    """Connect audit signal handlers (called from apps.py ready())"""
    from django.db.models.signals import pre_save, post_save

    pre_save.connect(
        capture_old_values,
        sender='training_records.TrainingRecord',
        dispatch_uid='training_record_capture_old_values',
    )
    post_save.connect(
        training_record_audit,
        sender='training_records.TrainingRecord',
        dispatch_uid='training_record_audit',
    )
