# training_records/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponse, FileResponse, HttpResponseForbidden
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
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from io import StringIO, BytesIO
import csv
from django.template.loader import render_to_string
from weasyprint import HTML, CSS
from django.conf import settings
import tempfile

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


# Replace your current export functions with these more robust versions

@login_required
def export_student_records(request, student_id, format='pdf'):
    """
    Export a student's training records as either PDF or CSV with improved error handling.
    """
    try:
        # Check permissions - only instructors or the student themselves can export
        if not (request.user.is_instructor() or request.user.id == int(student_id)):
            return HttpResponseForbidden("You don't have permission to export these records.")
        
        # Get the student
        student = get_object_or_404(User, id=student_id, user_type='student')
        
        # Get all records for this student, ordered by date
        records = TrainingRecord.objects.filter(
            student=student
        ).order_by('date')
        
        # Check if any records exist
        if not records.exists():
            messages.warning(request, "No training records found to export.")
            return redirect('record_list')
        
        if format.lower() == 'csv':
            return _export_csv(student, records)
        else:  # Default to PDF
            return _export_pdf_weasyprint(student, records, request)
    
    except Exception as e:
        # Log the detailed error with traceback
        import traceback
        logger.error(f"Error exporting records: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Show a user-friendly message
        messages.error(request, f"An error occurred while exporting records: {str(e)}")
        return redirect('record_list')

    
def _export_csv(student, records):
    """Generate a CSV export of student training records with proper UTF-8 encoding."""
    try:
        response = HttpResponse(
            content_type='text/csv; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename="{student.username}_training_records.csv"'},
        )
        
        # Add BOM (Byte Order Mark) for Excel to recognize UTF-8
        response.write('\ufeff')
        
        writer = csv.writer(response, quoting=csv.QUOTE_ALL)
        
        # Write header row
        writer.writerow([
            'Flight Number', 'Date', 'Topic', 'Glider', 'Location', 'Instructor',
            'Tow Height', 'Duration', 'Solo Flight', 'Student Comments', 
            'Instructor Comments', 'Signed Off', 'Sign Off Date'
        ])
        
        # Write data rows with robust error handling and proper UTF-8 encoding
        for record in records:
            # Handle potentially None values safely
            flight_number = record.get_flight_number() or ""
            date = record.date.strftime('%Y-%m-%d') if record.date else ""
            topic = record.training_topic.name if record.training_topic else ""
            glider = f"{record.glider.tail_number} ({record.glider.model})" if record.glider else ""
            location = record.field or ""
            
            # Handle instructor carefully
            if record.is_solo:
                instructor = "Solo Flight"
            else:
                instructor = record.instructor.get_full_name() if record.instructor else "Unknown"
            
            # Handle other fields
            tow_height = f"{record.tow_height} ft" if record.tow_height else ""
            duration = str(record.flight_duration) if record.flight_duration else ""
            solo = "Yes" if record.is_solo else "No"
            
            # Ensure text fields are properly handled as UTF-8
            student_comments = record.student_comments or ""
            instructor_comments = record.instructor_comments or ""
            signed_off = "Approved" if record.signed_off else "Not Approved"
            
            # Format timestamp carefully
            sign_off_date = ""
            if record.sign_off_timestamp:
                try:
                    sign_off_date = record.sign_off_timestamp.strftime('%Y-%m-%d %H:%M')
                except:
                    sign_off_date = str(record.sign_off_timestamp)
            
            # Write the row with safe values
            writer.writerow([
                flight_number, date, topic, glider, location, instructor,
                tow_height, duration, solo, student_comments,
                instructor_comments, signed_off, sign_off_date
            ])
        
        return response
    except Exception as e:
        # Log the error for debugging
        import traceback
        logger.error(f"CSV export error: {str(e)}")
        logger.error(traceback.format_exc())
        raise


def _export_pdf_weasyprint(student, records, request):
    """Generate a PDF export using WeasyPrint with HTML/CSS templates."""
    try:
        # Calculate summary statistics
        total_flights = records.count()
        solo_flights = records.filter(is_solo=True).count()
        signed_off_count = records.filter(signed_off=True).count()
        
        # Calculate total flight time
        total_duration = records.aggregate(total=Sum('flight_duration'))['total']
        total_flight_time = "0:00"
        if total_duration:
            total_seconds = int(total_duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            total_flight_time = f"{hours}:{minutes:02d}"
        
        # Process records to format durations and other data
        processed_records = []
        for record in records:
            # Format duration
            if record.flight_duration:
                total_seconds = int(record.flight_duration.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                formatted_duration = f"{hours}:{minutes:02d}"
            else:
                formatted_duration = "0:00"
            
            # Format instructor info
            if record.is_solo:
                instructor_name = "Solo Flight"
            else:
                instructor_name = record.instructor.get_full_name() if record.instructor else "Unknown"

            # Get instructor license for signature
            instructor_license = ""
            if record.instructor and record.instructor.instructor_license_number:
                instructor_license = record.instructor.instructor_license_number

            # Format glider info
            glider_info = f"{record.glider.tail_number} ({record.glider.model})" if record.glider else "N/A"

            # Add the processed record to the list
            processed_records.append({
                'id': record.id,
                'flight_number': record.get_flight_number() if hasattr(record, 'get_flight_number') else "",
                'date': record.date,
                'date_formatted': record.date.strftime('%Y-%m-%d') if record.date else "N/A",
                'topic': record.training_topic.name if record.training_topic else "N/A",
                'glider': glider_info,
                'field': record.field or "N/A",
                'instructor': instructor_name,
                'instructor_name': record.instructor.get_full_name() if record.instructor else "",
                'instructor_license': instructor_license,
                'tow_height': f"{record.tow_height} ft" if record.tow_height else "N/A",
                'duration': formatted_duration,
                'is_solo': record.is_solo,
                'student_comments': record.student_comments or "No comments provided.",
                'instructor_comments': record.instructor_comments or "No comments provided.",
                'signed_off': record.signed_off,
                'sign_off_timestamp': record.sign_off_timestamp.strftime('%Y-%m-%d %H:%M') if record.sign_off_timestamp else "N/A",
                'pre_solo_exercises': record.exercises.filter(category='pre-solo'),
                'post_solo_exercises': record.exercises.filter(category='post-solo'),
            })
        
        # Context for the template
        context = {
            'student': student,
            'records': processed_records,
            'total_flights': total_flights,
            'solo_flights': solo_flights,
            'signed_off_count': signed_off_count,
            'total_flight_time': total_flight_time,
            'current_date': timezone.now().strftime('%Y-%m-%d'),
            'rtl': True,  # Flag for RTL support
        }
        
        # Render the HTML template
        html_string = render_to_string('training_records/pdf_export_template.html', context)
        
        # Create a temporary file to write the PDF to
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            # Generate the PDF file
            HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(
                tmp.name,
                stylesheets=[
                    CSS(filename=os.path.join(settings.STATIC_ROOT, 'css', 'pdf_styles.css'))
                ]
            )
        
        # Read the PDF file into memory and return as a response
        with open(tmp.name, 'rb') as pdf_file:
            response = HttpResponse(pdf_file.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{student.username}_training_records.pdf"'
        
        # Clean up the temporary file
        os.unlink(tmp.name)
        
        return response
    
    except Exception as e:
        # Log the error for debugging
        import traceback
        logger.error(f"PDF export error: {str(e)}")
        logger.error(traceback.format_exc())
        raise