# training_records/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.utils import timezone
import uuid
import os
import posixpath

def get_secure_upload_path(instance, filename, subfolder):
    """
    Generate a secure random filename for uploaded files to prevent IDOR attacks.
    Ensures no path traversal is possible by using posixpath normalization.
    
    Args:
        instance: The model instance the file is being attached to
        filename: The original filename 
        subfolder: The subfolder to store files in
        
    Returns:
        A path with a random UUID-based filename while preserving the extension
    """
    # Get only the filename component without any path information to prevent path traversal
    filename = os.path.basename(filename)
    
    # Extract the file extension safely
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    
    # Generate a random filename with UUID to prevent guessing
    random_filename = f"{uuid.uuid4().hex}{ext}"
    
    # Construct path and normalize to prevent path traversal
    return posixpath.normpath(os.path.join(subfolder, random_filename))

def student_license_path(instance, filename):
    """Generate secure path for student license uploads"""
    return get_secure_upload_path(instance, filename, 'student_licenses')

def student_medical_path(instance, filename):
    """Generate secure path for student medical ID uploads"""
    return get_secure_upload_path(instance, filename, 'student_medical')

class User(AbstractUser):
    """Extended User model to differentiate between students and instructors"""
    USER_TYPE_CHOICES = (
        ('student', 'Student'),
        ('instructor', 'Instructor'),
        ('admin', 'Administrator'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    
    # Fields specific to students with secure file paths
    student_license_number = models.CharField(max_length=30, blank=True)
    student_license_photo = models.ImageField(upload_to=student_license_path, blank=True, null=True)
    student_medical_id_photo = models.ImageField(upload_to=student_medical_path, blank=True, null=True)
    
    # Fields specific to instructors
    instructor_license_number = models.CharField(max_length=30, blank=True)
    
    # Flag for first login (password change required)
    password_change_required = models.BooleanField(default=True)
    
    def is_student(self):
        return self.user_type == 'student'
    
    def is_instructor(self):
        return self.user_type == 'instructor'
    
    class Meta:
        db_table = 'auth_user'
        
class Glider(models.Model):
    """Model for glider aircraft information"""
    tail_number = models.CharField(max_length=10, unique=True)
    model = models.CharField(max_length=50)
    manufacturer = models.CharField(max_length=100)
    year = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.tail_number} ({self.model})"

class TrainingTopic(models.Model):
    """Predefined training topics for lessons"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=50, blank=True)
    required_for_certification = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name

class TrainingRecord(models.Model):
    """Core model for recording student training sessions"""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_records', 
                                limit_choices_to={'user_type': 'student'})
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='instructor_records', 
                                  limit_choices_to={'user_type': 'instructor'})
    training_topic = models.ForeignKey(TrainingTopic, on_delete=models.PROTECT)
    glider = models.ForeignKey(Glider, on_delete=models.PROTECT)
    is_solo = models.BooleanField(default=False, verbose_name="Solo Flight")
    
    # Training details
    date = models.DateField()
    field = models.CharField(max_length=100, help_text="Location/airfield where training took place")
    flight_duration = models.DurationField(validators=[MinValueValidator(timezone.timedelta(minutes=1))])
    student_comments = models.TextField(blank=True)
    instructor_comments = models.TextField(blank=True)
    
    # Exercises performed during this training session
    exercises = models.ManyToManyField('Exercise', related_name='training_records', blank=True)
    
    # Sign-off and verification
    signed_off = models.BooleanField(default=False)
    sign_off_timestamp = models.DateTimeField(null=True, blank=True)
    signature_hash = models.CharField(max_length=255, blank=True, help_text="Hash for digital signature verification")
    
    tow_height = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        help_text="Height of aerotow in feet"
    )
    
    # Add internal comments visible only to instructors
    internal_comments = models.TextField(
        blank=True, 
        help_text="Internal comments visible only to instructors"
    )
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_records')
    
    class Meta:
        ordering = ['-date', '-created_at']
        
    def __str__(self):
        return f"{self.student.username} - {self.training_topic} - {self.date}"
    
    def sign(self, instructor):
        """Method to sign off a training record"""
        if not self.signed_off and instructor.is_instructor() and instructor.id == self.instructor.id:
            self.signed_off = True
            self.sign_off_timestamp = timezone.now()
            
            # Generate a signature hash based on the record data and timestamp
            # This creates a unique hash that can verify the record hasn't been tampered with
            import hashlib
            data_string = (
                f"{self.id}|{self.student.id}|{self.instructor.id}|{self.training_topic.id}|"
                f"{self.glider.id}|{self.date}|{self.flight_duration}|{self.sign_off_timestamp}"
            )
            self.signature_hash = hashlib.sha256(data_string.encode()).hexdigest()
            
            self.save()
            
            # Log message can be accessed from audit log
            return True
        return False
    
    def get_flight_number(self):
        """Get this flight's number for the student (1-based)"""
        student_records = TrainingRecord.objects.filter(
            student=self.student, 
            date__lte=self.date
        ).order_by('date', 'created_at')
        
        for i, record in enumerate(student_records):
            if record.id == self.id:
                return i + 1  # 1-based indexing
        return None

class AuditLog(models.Model):
    """Audit logging for all changes to training records"""
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    action = models.CharField(max_length=50)
    table_name = models.CharField(max_length=50)
    record_id = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']

class Exercise(models.Model):
    """Model for specific flight exercises that can be performed during training"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    CATEGORY_CHOICES = (
        ('pre-solo', 'Pre-Solo'),
        ('post-solo', 'Post-Solo'),
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    # Optional numbering system for exercises
    number = models.CharField(max_length=10, blank=True, help_text="Exercise reference number")
    # Add to training requirement checklist
    is_required = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['category', 'number', 'name']
    
    def __str__(self):
        if self.number:
            return f"{self.number} - {self.name}"
        return self.name