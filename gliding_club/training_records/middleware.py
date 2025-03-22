# training_records/middleware.py
import json
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.db import models
import datetime
from django.forms.models import model_to_dict
from django.core.serializers.json import DjangoJSONEncoder  # Add this import

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
    """Get the changes made to a model instance"""
    if created:
        # New instance - capture all fields
        new_values = model_to_dict(instance)
        old_values = {}
    else:
        if not instance.pk:
            return {}, {}  # No changes to record

        # Existing instance - get original
        try:
            old_instance = instance.__class__.objects.get(pk=instance.pk)
            old_values = model_to_dict(old_instance)
            new_values = model_to_dict(instance)
        except instance.__class__.DoesNotExist:
            old_values = {}
            new_values = model_to_dict(instance)
    
    # Convert to safe JSON format
    safe_old_values = json.loads(json.dumps(old_values, cls=CustomJSONEncoder))
    safe_new_values = json.loads(json.dumps(new_values, cls=CustomJSONEncoder))
    
    return safe_old_values, safe_new_values

# Then modify your AuditLogMiddleware class's __call__ method to use this encoder
# when creating the AuditLog object:

def __call__(self, request):
    # Process the request
    response = self.get_response(request)
    
    # We only log actions that modify data
    if request.method not in ['GET', 'HEAD', 'OPTIONS'] and request.user.is_authenticated:
        # Log the action
        try:
            if hasattr(request, 'audit_data'):
                # Import here to avoid circular imports
                from .models import AuditLog
                
                for audit_entry in request.audit_data:
                    # Create a safe copy of the values for JSON serialization
                    old_values = json.loads(json.dumps(audit_entry.get('old_values', {}), cls=CustomJSONEncoder))
                    new_values = json.loads(json.dumps(audit_entry.get('new_values', {}), cls=CustomJSONEncoder))
                    
                    AuditLog.objects.create(
                        user=request.user,
                        action=audit_entry.get('action', request.method),
                        table_name=audit_entry.get('table_name', ''),
                        record_id=audit_entry.get('record_id', 0),
                        ip_address=self.get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        old_values=old_values,
                        new_values=new_values
                    )
        except Exception as e:
            # Log the error but don't interrupt the response
            print(f"Error creating audit log: {str(e)}")
            
    return response

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
        # Process the request
        response = self.get_response(request)
        
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
            except Exception as e:
                # Log the error but don't interrupt the response
                print(f"Error logging audit: {str(e)}")
                
        return response
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

# Model signal handlers for audit logging
def setup_audit_signals():
    """Set up signal handlers for audit logging"""
    from django.db.models.signals import pre_save, post_save
    from django.dispatch import receiver
    from django.forms.models import model_to_dict
    
    def get_model_changes(instance, created=False):
        """Get the changes made to a model instance"""
        if created:
            # New instance - capture all fields
            new_values = model_to_dict(instance)
            old_values = {}
        else:
            if not instance.pk:
                return {}, {}  # No changes to record

            # Existing instance - get original
            try:
                old_instance = instance.__class__.objects.get(pk=instance.pk)
                old_values = model_to_dict(old_instance)
                new_values = model_to_dict(instance)
            except instance.__class__.DoesNotExist:
                old_values = {}
                new_values = model_to_dict(instance)
                
        return old_values, new_values

    @receiver(post_save, sender='training_records.TrainingRecord')
    def training_record_audit(sender, instance, created, **kwargs):
        """Log changes to training records"""
        
        old_values, new_values = get_model_changes(instance, created)
        
        # Get the current request from thread local storage if available
        request = None
        import threading
        current_thread = threading.current_thread()
        if hasattr(current_thread, 'request'):
            request = current_thread.request
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            # If we have access to the request, add audit data to be processed by middleware
            if not hasattr(request, 'audit_data'):
                request.audit_data = []
                
            request.audit_data.append({
                'action': 'CREATE' if created else 'UPDATE',
                'table_name': instance._meta.db_table,
                'record_id': instance.pk,
                'old_values': old_values,
                'new_values': new_values
            })
        else:
            # If we don't have access to request, log directly
            # This is not ideal but ensures we still capture changes
            try:
                from .models import AuditLog, User
                admin_user = User.objects.filter(is_superuser=True).first()
                
                if admin_user:  # Only create log if we can find an admin user
                    AuditLog.objects.create(
                        user=admin_user,  # Use admin as fallback
                        action='CREATE' if created else 'UPDATE',
                        table_name=instance._meta.db_table,
                        record_id=instance.pk,
                        old_values=old_values,
                        new_values=new_values
                    )
            except Exception as e:
                print(f"Error creating audit log: {str(e)}")

# Call this function in your app's ready method to set up signals
# For example, in apps.py:
# def ready(self):
#     import training_records.middleware
#     training_records.middleware.setup_audit_signals()