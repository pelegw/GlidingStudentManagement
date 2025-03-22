# training_records/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.db.models import Q
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import Sum
import os 
from .models import TrainingRecord, TrainingTopic, Glider, User, Exercise
from .forms import TrainingRecordForm, SignOffForm, ProfileUpdateForm, PasswordChangeRequiredForm
from django.db import transaction
import logging
logger = logging.getLogger(__name__)
from django.core.files.storage import default_storage

class StudentRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_student()

class InstructorRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_instructor()

# Dashboard views
@login_required
def dashboard(request):
    """Main dashboard that redirects to the appropriate view based on user type"""
    if request.user.is_instructor():
        return redirect('instructor_dashboard')
    elif request.user.is_student():
        return redirect('student_dashboard')
    else:
        return redirect('admin:index')  # Fallback to admin

# Update in training_records/views.py

@login_required
def student_dashboard(request):
    """Dashboard view for students"""
    if not request.user.is_student():
        return HttpResponseForbidden("Students only")
    
    # Get student's training records
    training_records = TrainingRecord.objects.filter(student=request.user).order_by('-date')
    
    # Calculate stats
    total_flights = training_records.count()
    solo_flights_count = training_records.filter(is_solo=True).count()
    signed_off_count = training_records.filter(signed_off=True).count()
    pending_records = training_records.filter(signed_off=False)
    
    # Calculate total flight time
    total_duration = training_records.aggregate(total=Sum('flight_duration'))['total']
    
    # Format the duration for display
    total_flight_time = "0:00"
    if total_duration:
        total_seconds = int(total_duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        total_flight_time = f"{hours}:{minutes:02d}"
    
    context = {
        'training_records': training_records[:10],  # Latest 10 records
        'pending_records': pending_records,
        'total_flights': total_flights,
        'solo_flights_count': solo_flights_count,
        'signed_off_count': signed_off_count,
        'total_flight_time': total_flight_time,
    }
    
    return render(request, 'training_records/student_dashboard.html', context)

@login_required
def instructor_dashboard(request):
    if not request.user.is_instructor():
        return HttpResponseForbidden("Instructors only")
    
    # Get recent training records where this user is the instructor
    instructor_records = TrainingRecord.objects.filter(instructor=request.user).order_by('-date')
    
    # Get unsigned records that need attention
    unsigned_records = instructor_records.filter(signed_off=False).order_by('-date')
    
    # Calculate total flights and flight time
    total_flights = instructor_records.count()
    
    # Calculate total flight time
    total_duration = instructor_records.aggregate(total=Sum('flight_duration'))['total']
    # Format the duration for display
    total_flight_time = "0:00:00"
    if total_duration:
        total_seconds = int(total_duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        total_flight_time = f"{hours}:{minutes:02d}:{seconds:02d}"
    
    # Count of students taught
    students_count = instructor_records.values('student').distinct().count()
    
    # Get all students for the lookup feature
    all_students = User.objects.filter(user_type='student').order_by('first_name', 'last_name')
    
    # Get recent students with training count
    from django.db.models import Count
    
    recent_students = User.objects.filter(
        user_type='student',
        student_records__instructor=request.user
    ).annotate(
        training_count=Count('student_records')
    ).order_by('-student_records__date')[:5]
    
    # Make recent_students distinct
    recent_students = list(dict.fromkeys(recent_students))
    
    context = {
        'instructor_records': instructor_records[:10],  # Latest 10 records
        'unsigned_records': unsigned_records,
        'total_flights': total_flights,
        'total_flight_time': total_flight_time,
        'students_count': students_count,
        'pending_count': unsigned_records.count(),
        'all_students': all_students,
        'recent_students': recent_students,
    }
    
    return render(request, 'training_records/instructor_dashboard.html', context)

# Training Record views
class TrainingRecordListView(LoginRequiredMixin, ListView):
    """List all training records the user has access to"""
    model = TrainingRecord
    template_name = 'training_records/record_list.html'
    context_object_name = 'records'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = TrainingRecord.objects.all().order_by('-date')
        
        # Filter based on user type
        if self.request.user.is_student():
            queryset = queryset.filter(student=self.request.user)
        elif self.request.user.is_instructor():
            # Instructors can see their own records and any unsigned records
            queryset = queryset.filter(
                Q(instructor=self.request.user) | 
                Q(signed_off=False)
            )
        # Admin users can see all records
        
        # Add search functionality
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(student__username__icontains=search_query) |
                Q(instructor__username__icontains=search_query) |
                Q(training_topic__name__icontains=search_query) |
                Q(glider__tail_number__icontains=search_query)
            )
            
        return queryset

class TrainingRecordDetailView(LoginRequiredMixin, DetailView):
    """Detail view for a training record"""
    model = TrainingRecord
    template_name = 'training_records/record_detail.html'
    context_object_name = 'record'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_sign'] = (
            self.request.user.is_instructor() and 
            self.object.instructor == self.request.user and
            not self.object.signed_off
        )

        # Format the duration as HH:MM
        duration = self.object.flight_duration
        if duration:
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            context['formatted_duration'] = f"{hours}:{minutes:02d}"
        else:
            context['formatted_duration'] = "0:00"

        # Filter exercises by category
        context['pre_solo_exercises'] = self.object.exercises.filter(category='pre-solo')
        context['post_solo_exercises'] = self.object.exercises.filter(category='post-solo')

        return context

# Update in training_records/views.py

class TrainingRecordCreateView(LoginRequiredMixin, CreateView):
    """Create a new training record"""
    model = TrainingRecord
    form_class = TrainingRecordForm
    template_name = 'training_records/record_form.html'
    success_url = reverse_lazy('record_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add split exercises lists to context
        context['all_pre_solo_exercises'] = Exercise.objects.filter(category='pre-solo').order_by('number', 'name')
        context['all_post_solo_exercises'] = Exercise.objects.filter(category='post-solo').order_by('number', 'name')
        
        return context
    
    def form_valid(self, form):
        # Set the student to the current user if they're a student
        if self.request.user.is_student():
            form.instance.student = self.request.user
        
        messages.success(self.request, 'Training record created successfully.')
        return super().form_valid(form)

class TrainingRecordUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing training record"""
    model = TrainingRecord
    form_class = TrainingRecordForm
    template_name = 'training_records/record_form.html'
    
    def get_success_url(self):
        return reverse_lazy('record_detail', kwargs={'pk': self.object.pk})
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add split exercises lists to context
        context['all_pre_solo_exercises'] = Exercise.objects.filter(category='pre-solo').order_by('number', 'name')
        context['all_post_solo_exercises'] = Exercise.objects.filter(category='post-solo').order_by('number', 'name')
        
        return context
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Students can only edit unsigned records they're part of
        if self.request.user.is_student():
            return queryset.filter(student=self.request.user, signed_off=False)
        
        # Instructors can edit any record they instructed
        if self.request.user.is_instructor():
            return queryset.filter(instructor=self.request.user)
        
        # Admins can edit any record
        return queryset

# Profile management views
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
                    form.save()
                    
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
    """Force password change on first login"""
    # If password change not required, redirect to dashboard
    if not request.user.password_change_required:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = PasswordChangeRequiredForm(request.POST)
        if form.is_valid():
            # Set the new password
            request.user.set_password(form.cleaned_data['new_password1'])
            request.user.password_change_required = False
            request.user.save()
            
            # Update the session to prevent logging out
            update_session_auth_hash(request, request.user)
            
            messages.success(request, "Your password has been changed successfully. You can now access the system.")
            return redirect('dashboard')
    else:
        form = PasswordChangeRequiredForm()
    
    return render(request, 'training_records/first_login.html', {'form': form})

# Sign-off functionality
@login_required
def sign_record(request, pk):
    """Allow instructors to sign off on a training record"""
    record = get_object_or_404(TrainingRecord, pk=pk)
    
    # Only the instructor assigned to the record can sign it off
    if not request.user.is_instructor() or request.user != record.instructor:
        return HttpResponseForbidden("You are not authorized to sign off this record.")
    
    # Can't sign off a record that's already signed
    if record.signed_off:
        messages.warning(request, "This record has already been signed off.")
        return redirect('record_detail', pk=record.pk)
    
    if request.method == 'POST':
        form = SignOffForm(request.POST)
        if form.is_valid():
            # Perform the sign-off
            instructor_comments = form.cleaned_data['instructor_comments']
            internal_comments = form.cleaned_data['internal_comments']

            # Update record with comments
            if instructor_comments:
                record.instructor_comments = instructor_comments
            if internal_comments:
                record.internal_comments = internal_comments


            record.sign(request.user)
            record.save()
            # Create a log entry (this is already handled by our signal handler)
            messages.success(request, f"Training record #{record.pk} has been successfully signed off.")
            return redirect('record_detail', pk=record.pk)
    else:
        form = SignOffForm(initial={
            'instructor_comments': record.instructor_comments,
            'internal_comments': record.internal_comments
        })
    
    return render(request, 'training_records/sign_record.html', {
        'form': form,
        'record': record
    })
@login_required
def student_history(request, student_id):
    # Check if user is an instructor
    if not request.user.is_instructor():
        return HttpResponseForbidden("Only instructors can view student histories")
    
    # Get the student
    student = get_object_or_404(User, pk=student_id, user_type='student')
    
    # Get all training records for this student (regardless of instructor)
    training_records = TrainingRecord.objects.filter(student=student).order_by('-date')
    
    # Calculate statistics
    total_flights = training_records.count()
    solo_flights = training_records.filter(is_solo=True).count()
    signed_off_count = training_records.filter(signed_off=True).count()
    
    # Calculate total flight time
    total_duration = training_records.aggregate(total=Sum('flight_duration'))['total']
    # Format the duration for display
    total_flight_time = "0:00"
    if total_duration:
        total_seconds = int(total_duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        total_flight_time = f"{hours}:{minutes:02d}"
    
    # Get all exercises completed by the student
    completed_exercises = Exercise.objects.filter(
        training_records__student=student,
        training_records__signed_off=True
    ).distinct()
    
    # Get pre-solo and post-solo exercises separately
    pre_solo_exercises = completed_exercises.filter(category='pre-solo')
    post_solo_exercises = completed_exercises.filter(category='post-solo')
    
    # Find all instructors who worked with this student
    instructors = User.objects.filter(
        instructor_records__student=student
    ).distinct()
    
    context = {
        'student': student,
        'training_records': training_records,
        'total_flights': total_flights,
        'solo_flights': solo_flights,
        'signed_off_count': signed_off_count,
        'total_flight_time': total_flight_time,
        'pre_solo_exercises': pre_solo_exercises,
        'post_solo_exercises': post_solo_exercises,
        'instructors': instructors,
    }
    
    return render(request, 'training_records/student_history.html', context)


@login_required
def student_lookup(request):
    # Check if user is an instructor
    if not request.user.is_instructor():
        return HttpResponseForbidden("Only instructors can look up students")
    
    # If a student ID is provided, redirect to the student history page
    student_id = request.GET.get('student_id')
    if student_id:
        return redirect('student_history', student_id=student_id)
    
    # Get all students for the lookup form
    all_students = User.objects.filter(user_type='student').order_by('first_name', 'last_name')
    
    # Get recent records for quick access
    recent_records = TrainingRecord.objects.all().order_by('-date')[:20]
    
    # Group students with their most recent training topic
    from django.db.models import Max
    
    students_with_recent_activity = User.objects.filter(
        user_type='student',
        student_records__isnull=False
    ).annotate(
        last_training_date=Max('student_records__date')
    ).order_by('-last_training_date')[:15]
    
    # Get the most recent training topic for each student
    for student in students_with_recent_activity:
        recent_record = TrainingRecord.objects.filter(
            student=student
        ).order_by('-date').first()
        
        if recent_record:
            student.recent_topic = recent_record.training_topic.name
            student.recent_date = recent_record.date
    
    context = {
        'all_students': all_students,
        'students_with_recent_activity': students_with_recent_activity,
        'recent_records': recent_records,
    }
    
    return render(request, 'training_records/student_lookup.html', context)