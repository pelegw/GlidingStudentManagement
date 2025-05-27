# training_records/admin.py
from django.contrib import admin,messages
from django.contrib.auth.admin import UserAdmin
from django.db import transaction
from .models import (
    User, Glider, TrainingTopic, TrainingRecord, AuditLog, 
    Exercise, GroundBriefingTopic, GroundBriefing, ExercisePerformance
)
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'license_expiration_date', 'is_active')
    list_filter = ('user_type', 'is_active', 'is_staff', 'license_expiration_date')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Student Info', {'fields': ('student_license_number', 'student_license_photo', 'student_medical_id_photo')}),
        ('Instructor Info', {'fields': ('instructor_license_number',)}),
        ('License Info', {'fields': ('license_expiration_date',)}),  # Add this section
        ('Permissions', {'fields': ('user_type', 'is_active', 'is_staff', 'is_superuser', 'password_change_required', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'user_type', 'license_expiration_date'),
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
@admin.register(TrainingRecord)
class TrainingRecordAdmin(admin.ModelAdmin):
    list_display = ('date', 'student', 'instructor', 'training_topic', 'glider', 'flight_duration', 'signed_off')
    list_filter = ('date', 'signed_off', 'training_topic')
    search_fields = ('student__username', 'instructor__username', 'training_topic__name', 'glider__tail_number')
    readonly_fields = ('created_at', 'updated_at', 'sign_off_timestamp', 'signature_hash')
    filter_horizontal = ('exercises',)  # Easier management of many-to-many relationship
    actions = ['delete_all_student_data']

    def delete_all_student_data(self, request, queryset):
        # Check if user is superuser
        if not request.user.is_superuser:
            messages.error(request, "Only superusers can perform this action.")
            return
        
        try:
            # Get counts first
            training_count = TrainingRecord.objects.count()
            briefing_count = GroundBriefing.objects.count() 
            exercise_count = ExercisePerformance.objects.count()
            
            # Check if there's anything to delete
            total_count = training_count + briefing_count + exercise_count
            if total_count == 0:
                messages.info(request, "No student data found to delete.")
                return
            
            # Delete everything
            ExercisePerformance.objects.all().delete()
            GroundBriefing.objects.all().delete()
            TrainingRecord.objects.all().delete()
            
            # Success message
            messages.success(
                request, 
                f"Successfully deleted {training_count} training records, "
                f"{briefing_count} ground briefings, and "
                f"{exercise_count} exercise performances."
            )
        
        except Exception as e:
            messages.error(request, f"Error deleting data: {e}")

    def save_model(self, request, obj, form, change):
        """Override save_model to capture the user making the change"""
        # Track who created the record if it's new
        if not change and not obj.created_by:
            obj.created_by = request.user
            
        import threading
        current_thread = threading.current_thread()
        current_thread.request = request
        super().save_model(request, obj, form, change)

    delete_all_student_data.short_description = "🗑️ DELETE ALL STUDENT DATA (DANGER!)"

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

@admin.register(GroundBriefingTopic)
class GroundBriefingTopicAdmin(admin.ModelAdmin):
    list_display = ('number', 'name')
    search_fields = ('name', 'details')
    ordering = ['number']

@admin.register(GroundBriefing)
class GroundBriefingAdmin(admin.ModelAdmin):
    list_display = ('student', 'topic', 'date', 'instructor', 'signed_off', 'sign_off_date')
    list_filter = ('signed_off', 'date', 'topic')
    search_fields = ('student__username', 'student__first_name', 'instructor__username')
    raw_id_fields = ('student', 'instructor')
    date_hierarchy = 'date'