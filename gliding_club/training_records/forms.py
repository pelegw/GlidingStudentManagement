# training_records/forms.py
from django import forms
from django.core.validators import MinValueValidator
from django.utils import timezone
from .models import TrainingRecord, User, Glider, TrainingTopic,Exercise,ExercisePerformance
import os
from django.core.exceptions import ValidationError
from PIL import Image
import io
from datetime import timedelta
import re

class ExercisePerformanceForm(forms.ModelForm):
    """Form for a single exercise performance within a training record"""
    class Meta:
        model = ExercisePerformance
        fields = ['exercise', 'performance', 'notes']
        widgets = {
            'exercise': forms.HiddenInput(),
            'performance': forms.RadioSelect(),
            'notes': forms.Textarea(attrs={'rows': 1, 'placeholder': 'Optional notes'})
        }


class TrainingRecordForm(forms.ModelForm):
    """Form for creating and editing training records with exercise performances"""
    
    # Duration display field
    duration_display = forms.CharField(
        label="Flight Duration (HH:MM)",
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'HH:MM'})
    )
    
    # Solo flight checkbox
    is_solo = forms.BooleanField(
        label="Solo Flight",
        required=False,
        help_text="Check this box if this was a solo flight (no instructor present)"
    )
    
    class Meta:
        model = TrainingRecord
        fields = [
            'instructor', 'training_topic', 'glider',
            'date', 'field', 'tow_height',
            'student_comments'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'student_comments': forms.Textarea(attrs={'rows': 3, 'class': 'form-control w-100'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Instructor choices
        self.fields['instructor'].queryset = User.objects.filter(user_type='instructor')
        self.fields['instructor'].help_text = "Select the instructor for this training session"
        
        # Glider choices
        self.fields['glider'].queryset = Glider.objects.filter(is_active=True)
        
        # Default date
        if not self.instance.pk:
            self.fields['date'].initial = timezone.now().date()
        
        # Set initial value for duration
        if self.instance and self.instance.pk and self.instance.flight_duration:
            total_minutes = self.instance.flight_duration.total_seconds() // 60
            hours = total_minutes // 60
            minutes = total_minutes % 60
            self.fields['duration_display'].initial = f"{int(hours)}:{int(minutes):02d}"
        
        # For student users
        if self.user and self.user.is_student():
            # Make instructor field required even for solo flights
            self.fields['instructor'].required = True
            
            # If record is signed off, disable all fields
            if self.instance and self.instance.signed_off:
                for field in self.fields:
                    self.fields[field].widget.attrs['readonly'] = True

        # For instructor users
        elif self.user and self.user.is_instructor():
            # Pre-select the instructor if creating new record
            if not self.instance.pk:
                self.fields['instructor'].initial = self.user
            
            # If record belongs to another instructor, disable fields
            if self.instance and self.instance.instructor != self.user:
                for field in self.fields:
                    self.fields[field].widget.attrs['readonly'] = True
            
            # If record is signed off, disable all fields
            if self.instance and self.instance.signed_off:
                for field in self.fields:
                    self.fields[field].widget.attrs['readonly'] = True
    
    def clean_duration_display(self):
        """Convert HH:MM to timedelta"""
        duration_str = self.cleaned_data.get('duration_display', '')
        
        try:
            hours, minutes = map(int, duration_str.split(':'))
            if minutes >= 60:
                raise forms.ValidationError("Minutes should be less than 60")
            
            # Convert to timedelta
            duration = timedelta(hours=hours, minutes=minutes)
            
            # Ensure duration is positive
            if duration.total_seconds() <= 0:
                raise forms.ValidationError("Flight duration must be greater than zero")
                
            return duration
        except ValueError:
            raise forms.ValidationError("Invalid duration format. Use HH:MM (e.g., 1:30)")
    
    def clean(self):
        """Additional validation rules"""
        cleaned_data = super().clean()
        
        # Get duration from duration_display
        if 'duration_display' in cleaned_data:
            # Set the actual flight_duration field
            self.instance.flight_duration = cleaned_data['duration_display']
        
        # Ensure the record isn't being modified if it's already signed off
        if self.instance and self.instance.pk and self.instance.signed_off:
            raise forms.ValidationError("Cannot modify a record that has been signed off.")
        
        return cleaned_data

ExercisePerformanceFormSet = forms.inlineformset_factory(
    TrainingRecord, 
    ExercisePerformance,
    form=ExercisePerformanceForm,
    extra=0,  # No extra forms by default
    can_delete=False  # Don't allow deletion (all exercises should have a state)
)


class SignOffForm(forms.ModelForm):
    """Form for instructors to sign off on a training record with ability to edit flight details"""
    
    confirm_sign_off = forms.BooleanField(
        label="I confirm that this training record is accurate and complete",
        required=True
    )
    
    duration_display = forms.CharField(
        label="Flight Duration (HH:MM)",
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'HH:MM'})
    )
    
    class Meta:
        model = TrainingRecord
        fields = [
            'date', 'glider', 'training_topic', 'field', 'tow_height',
            'is_solo', 'student_comments', 'instructor_comments'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'student_comments': forms.Textarea(attrs={'rows': 3}),
            'instructor_comments': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set initial value for duration
        if self.instance and self.instance.pk and self.instance.flight_duration:
            total_minutes = self.instance.flight_duration.total_seconds() // 60
            hours = total_minutes // 60
            minutes = total_minutes % 60
            self.fields['duration_display'].initial = f"{int(hours)}:{int(minutes):02d}"
        
        # Help text for comments
        self.fields['instructor_comments'].help_text = "Comments that will be visible to the student"
        self.fields['student_comments'].help_text = "Student's original comments (can be edited if needed)"
    
    def clean_duration_display(self):
        """Convert HH:MM to timedelta"""
        duration_str = self.cleaned_data.get('duration_display', '')
        
        try:
            hours, minutes = map(int, duration_str.split(':'))
            if minutes >= 60:
                raise forms.ValidationError("Minutes should be less than 60")
            
            # Convert to timedelta
            duration = timedelta(hours=hours, minutes=minutes)
            
            # Ensure duration is positive
            if duration.total_seconds() <= 0:
                raise forms.ValidationError("Flight duration must be greater than zero")
                
            return duration
        except ValueError:
            raise forms.ValidationError("Invalid duration format. Use HH:MM (e.g., 1:30)")
    
    def clean(self):
        """Additional validation rules"""
        cleaned_data = super().clean()
        
        # Get duration from duration_display
        if 'duration_display' in cleaned_data:
            # Set the actual flight_duration field
            self.instance.flight_duration = cleaned_data['duration_display']
        
        # Validate that the record wasn't already signed off
        if self.instance and self.instance.pk and self.instance.signed_off:
            raise forms.ValidationError("Cannot modify a record that has already been signed off.")
        
        return cleaned_data
    
    def save(self, commit=True):
        """Override save to handle the flight_duration field"""
        instance = super().save(commit=False)
        
        # Preserve the is_solo value from the original record
        if self.instance and self.instance.pk:
            # This ensures we don't change the solo status even though it's hidden
            instance.is_solo = self.instance.is_solo
        
        if commit:
            instance.save()
            self.save_m2m()
        
        return instance


# Update in training_records/forms.py


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'student_license_number', 'student_license_photo', 'student_medical_id_photo',
            'instructor_license_number'
        ]
    
    def __init__(self, *args, **kwargs):
        user = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        
        # Add help text
        self.fields['student_license_photo'].help_text = "Upload an image of your student license (JPEG, PNG formats only, max 5MB)"
        self.fields['student_medical_id_photo'].help_text = "Upload an image of your medical ID (JPEG, PNG formats only, max 5MB)"
        
        # Show only relevant fields based on user type
        if user and user.is_instructor():
            # Hide student-specific fields for instructors
            self.fields['student_license_number'].widget = forms.HiddenInput()
            self.fields['student_license_photo'].widget = forms.HiddenInput()
            self.fields['student_medical_id_photo'].widget = forms.HiddenInput()
        elif user and user.is_student():
            # Hide instructor-specific fields for students
            self.fields['instructor_license_number'].widget = forms.HiddenInput()
    
    def validate_image_file(self, file_obj):
        """
        Thoroughly validate that a file is a proper image
        
        Args:
            file_obj: The uploaded file object
            
        Raises:
            ValidationError: If the file is not a valid image or has security issues
        """
        if not file_obj:
            return
        
        # Check file size (5MB limit)
        if file_obj.size > 5 * 1024 * 1024:
            raise ValidationError("Image file size must be less than 5MB")
        
        # Validate that the file is actually an image using PIL
        try:
            # Read image data into memory
            file_data = file_obj.read()
            
            # Seek back to the beginning of the file for future operations
            file_obj.seek(0)
            
            # Try to open as an image
            img = Image.open(io.BytesIO(file_data))
            
            # Verify image integrity by loading it
            img.verify()
            
            # Check image format
            if img.format not in ['JPEG', 'PNG']:
                raise ValidationError("Only JPEG and PNG image formats are allowed")
                
            # You can add more image validation here if needed
            # For example:
            # - Check image dimensions
            # - Check metadata
            
        except Exception as e:
            raise ValidationError(f"Invalid image file: {str(e)}")
    
    def clean_student_license_photo(self):
        """Validate student license photo upload"""
        photo = self.cleaned_data.get('student_license_photo')
        if photo:
            self.validate_image_file(photo)
        return photo
    
    def clean_student_medical_id_photo(self):
        """Validate student medical ID photo upload"""
        photo = self.cleaned_data.get('student_medical_id_photo')
        if photo:
            self.validate_image_file(photo)
        return photo

class PasswordChangeRequiredForm(forms.Form):
    """Form for users to change their password on first login"""
    new_password1 = forms.CharField(
        label="New password",
        widget=forms.PasswordInput,
        strip=False,
    )
    new_password2 = forms.CharField(
        label="New password confirmation",
        widget=forms.PasswordInput,
        strip=False,
    )
    
    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("The two password fields didn't match.")
        return password2