from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.contrib.auth.forms import PasswordChangeForm
from django.core.files.storage import default_storage
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
import logging

from ..models import User
from ..forms import ProfileUpdateForm, PasswordChangeRequiredForm

logger = logging.getLogger(__name__)
@login_required
def profile_view(request):
    """View user profile details"""
    return render(request, 'training_records/profile.html', {'user': request.user})

@login_required
def profile_update(request):
    """
    Update user profile with secure file handling.
    
    Ensures:
    - Only authorized users can update profiles
    - Image validation is performed
    - Old files are cleaned up securely using Django's storage API
    - Transactions prevent partial updates
    """
    if not (request.user.is_student() or request.user.is_instructor()):
        messages.error(request, "Only students and instructors can update their profile information.")
        return redirect('profile')
    
    if request.method == 'POST':
        # Get a copy of the user to access old file names through Django's storage API
        old_user = User.objects.get(pk=request.user.pk)
        
        # Store file names only (not paths) using Django's storage methods
        old_license_name = old_user.student_license_photo.name if old_user.student_license_photo else None
        old_medical_name = old_user.student_medical_id_photo.name if old_user.student_medical_id_photo else None
        
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Save the form with transaction to ensure atomicity
                    updated_user = form.save()
                    
                    if updated_user.license_expiration_date:
                        if updated_user.is_license_expired():
                            messages.warning(request, "Warning: Your license has expired. Please renew it as soon as possible.")
                        elif updated_user.is_license_expiring_soon():
                            messages.warning(request, "Notice: Your license expires within 30 days. Consider renewing it soon.")
                    
                    # Clean up old files if they were replaced using Django's storage API
                    if 'student_license_photo' in request.FILES and old_license_name:
                        # Get the new name
                        new_license_name = request.user.student_license_photo.name
                        
                        # Only delete if the file names are different
                        if old_license_name != new_license_name:
                            try:
                                # Use default_storage to safely delete the file
                                if default_storage.exists(old_license_name):
                                    default_storage.delete(old_license_name)
                            except Exception as e:
                                # Log error but continue - file cleanup isn't critical
                                logger.warning(f"Could not remove old license photo: {e}")
                    
                    if 'student_medical_id_photo' in request.FILES and old_medical_name:
                        # Get the new name
                        new_medical_name = request.user.student_medical_id_photo.name
                        
                        # Only delete if the file names are different
                        if old_medical_name != new_medical_name:
                            try:
                                # Use default_storage to safely delete the file
                                if default_storage.exists(old_medical_name):
                                    default_storage.delete(old_medical_name)
                            except Exception as e:
                                # Log error but continue - file cleanup isn't critical
                                logger.warning(f"Could not remove old medical ID photo: {e}")
                
                messages.success(request, "Your profile has been updated successfully.")
                return redirect('profile')
                
            except Exception as e:
                logger.error(f"Error updating profile for user {request.user.id}: {str(e)}")
                messages.error(request, "An error occurred while updating your profile. Please try again.")
    else:
        form = ProfileUpdateForm(instance=request.user)
    
    return render(request, 'training_records/profile_update.html', {'form': form})


# Password change views
@login_required
def change_password(request):
    """Standard password change view"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Update the session to prevent logging out
            update_session_auth_hash(request, user)
            messages.success(request, "Your password was successfully updated!")
            return redirect('dashboard')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'training_records/change_password.html', {'form': form})


@login_required
def first_login_password_change(request):
    if not request.user.password_change_required:
        return redirect('dashboard')

    if request.method == 'POST':
        form = PasswordChangeRequiredForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data['new_password1']
            
            # Validate password against your configured validators
            try:
                validate_password(password, request.user)
                
                # If validation passes, set the password
                request.user.set_password(password)
                request.user.password_change_required = False
                request.user.save()
                
                # Update session
                update_session_auth_hash(request, request.user)
                
                messages.success(request, "Your password has been changed successfully. You can now access the system.")
                return redirect('dashboard')
                
            except ValidationError as error:
                # Add validation errors to the form
                form.add_error('new_password1', error)
    else:
        form = PasswordChangeRequiredForm()

    return render(request, 'training_records/first_login.html', {'form': form})
