# training_records/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Glider, TrainingTopic, TrainingRecord, AuditLog, Exercise
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_active')
    list_filter = ('user_type', 'is_active', 'is_staff')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Student Info', {'fields': ('student_license_number', 'student_license_photo', 'student_medical_id_photo')}),
        ('Instructor Info', {'fields': ('instructor_license_number',)}),
        ('Permissions', {'fields': ('user_type', 'is_active', 'is_staff', 'is_superuser', 'password_change_required', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'user_type'),
        }),
    )
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)

@admin.register(Glider)
class GliderAdmin(admin.ModelAdmin):
    list_display = ('tail_number', 'model', 'manufacturer', 'year', 'is_active')
    list_filter = ('is_active', 'manufacturer')
    search_fields = ('tail_number', 'model')

@admin.register(TrainingTopic)
class TrainingTopicAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'required_for_certification')
    list_filter = ('category', 'required_for_certification')
    search_fields = ('name', 'description')

# Update TrainingRecordAdmin to include exercises
class TrainingRecordAdmin(admin.ModelAdmin):
    list_display = ('date', 'student', 'instructor', 'training_topic', 'glider', 'flight_duration', 'signed_off')
    list_filter = ('date', 'signed_off', 'training_topic')
    search_fields = ('student__username', 'instructor__username', 'training_topic__name', 'glider__tail_number')
    readonly_fields = ('created_at', 'updated_at', 'sign_off_timestamp', 'signature_hash')
    filter_horizontal = ('exercises',)  # Easier management of many-to-many relationship

    def save_model(self, request, obj, form, change):
        """Override save_model to capture the user making the change"""
        # Track who created the record if it's new
        if not change and not obj.created_by:
            obj.created_by = request.user
            
        import threading
        current_thread = threading.current_thread()
        current_thread.request = request
        super().save_model(request, obj, form, change)

admin.site.register(TrainingRecord, TrainingRecordAdmin)

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'table_name', 'record_id', 'ip_address')
    list_filter = ('action', 'timestamp', 'table_name')
    search_fields = ('user__username', 'table_name', 'ip_address')
    readonly_fields = ('timestamp', 'user', 'action', 'table_name', 'record_id', 
                       'ip_address', 'user_agent', 'old_values', 'new_values')

@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ('name', 'number', 'category', 'is_required')
    list_filter = ('category', 'is_required')
    search_fields = ('name', 'description', 'number')
    ordering = ('category', 'number', 'name')