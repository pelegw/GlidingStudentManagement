# training_records/views/instructor.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse,HttpResponseForbidden
from django.db.models import Sum, Count, Max, Q
from ..models import TrainingRecord, User, GroundBriefing, Exercise
from ..forms import SignOffForm, GroundBriefingSignOffForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, date, timedelta
from django.core.paginator import Paginator
import csv
from datetime import datetime
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

@login_required
def instructor_dashboard(request):
    if not request.user.is_instructor():
        return HttpResponseForbidden("Instructors only")
    
    # Get all training records where this user is the instructor
    all_instructor_records = TrainingRecord.objects.filter(instructor=request.user).order_by('-date', '-created_at')
    
    # Separate instructional flights (instructor on board) from supervised solo flights
    instructional_records = all_instructor_records.filter(is_solo=False)
    supervised_solo_records = all_instructor_records.filter(is_solo=True)
    
    # Get unsigned records that need attention (both types)
    unsigned_records = all_instructor_records.filter(signed_off=False).order_by('-date')
    
    # Calculate instructional flights statistics
    total_instructional_flights = instructional_records.count()
    total_supervised_solo_flights = supervised_solo_records.count()
    
    # Calculate total flight time (only from instructional flights - no seconds)
    instructional_duration = instructional_records.aggregate(total=Sum('flight_duration'))['total']
    total_flight_time = "0:00"
    if instructional_duration:
        total_seconds = int(instructional_duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        total_flight_time = f"{hours}:{minutes:02d}"
    
    # Count of students taught (from both types of flights)
    students_count = all_instructor_records.values('student').distinct().count()
    
    # Get all students for the lookup feature
    all_students = User.objects.filter(user_type='student').order_by('first_name', 'last_name')
    
    # Get recent students with training count
    recent_students = User.objects.filter(
        user_type='student',
        student_records__instructor=request.user
    ).annotate(
        training_count=Count('student_records')
    ).order_by('-student_records__date')[:5]
    
    # Make recent_students distinct
    recent_students = list(dict.fromkeys(recent_students))
    
    pending_briefings = GroundBriefing.objects.filter(
        instructor=request.user,
        signed_off=False
    ).select_related('student', 'topic').order_by('date')

    context = {
        'instructor_records': all_instructor_records[:10],  # Latest 10 records (both types)
        'unsigned_records': unsigned_records,
        'total_instructional_flights': total_instructional_flights,  # Changed from total_flights
        'total_supervised_solo_flights': total_supervised_solo_flights,  # New
        'total_flight_time': total_flight_time,  # Now without seconds
        'students_count': students_count,
        'pending_count': unsigned_records.count(),
        'all_students': all_students,
        'recent_students': recent_students,
        'pending_briefings': pending_briefings,
    }

    return render(request, 'training_records/instructor_dashboard.html', context)


@login_required
def sign_record(request, pk):
    """Allow instructors to sign off on a training record and edit flight details"""
    record = get_object_or_404(TrainingRecord, pk=pk)
    
    # Only the instructor assigned to the record can sign it off
    if not request.user.is_instructor() or request.user != record.instructor:
        return HttpResponseForbidden("You are not authorized to sign off this record.")
    
    # Check if record is still modifiable (either unsigned or within 7-day window)
    if record.signed_off and not record.is_modifiable_by_instructor(request.user):
        days_since_signoff = (timezone.now() - record.sign_off_timestamp).days if record.sign_off_timestamp else 0
        messages.error(
            request, 
            f"This record was signed off {days_since_signoff} days ago. "
            "Modifications are only allowed within 7 days of sign-off."
        )
        return redirect('record_detail', pk=record.pk)
    
    # Show warning if within modification window
    modification_warning = None
    if record.signed_off:
        days_remaining = record.days_until_modification_deadline()
        if days_remaining is not None:
            modification_warning = f"⚠️ This record was already signed off. You have {days_remaining} day(s) remaining to make modifications."
    
    if request.method == 'POST':
        form = SignOffForm(request.POST, instance=record)
        if form.is_valid():
            # Save the updated record
            updated_record = form.save()
            
            # Perform the sign-off if confirmed and not already signed
            if form.cleaned_data.get('confirm_sign_off') and not record.signed_off:
                updated_record.sign(request.user)
                updated_record.save()
                messages.success(request, f"Training record #{record.pk} has been successfully updated and signed off.")
            else:
                # Just updating an already signed record
                if record.signed_off:
                    messages.success(request, f"Training record #{record.pk} has been updated successfully.")
                else:
                    messages.success(request, f"Training record #{record.pk} has been updated but not signed off yet.")
            
            return redirect('record_detail', pk=record.pk)
    else:
        form = SignOffForm(instance=record)
    
    context = {
        'form': form,
        'record': record,
        'modification_warning': modification_warning,
        'is_modification': record.signed_off,  # Flag to adjust UI
    }
    
    return render(request, 'training_records/sign_record.html', context)

@login_required
def student_history(request, student_id):
    # Check if user is an instructor
    if not request.user.is_instructor():
        return HttpResponseForbidden("Only instructors can view student histories")
    
    # Get the student
    student = get_object_or_404(User, pk=student_id, user_type='student')
    
    # Get all training records for this student (regardless of instructor)
    training_records = TrainingRecord.objects.filter(student=student).order_by('-date', '-created_at')
    
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

# Update training_records/views/instructor.py
@login_required
def instructor_flight_history(request):
    """View all flights for an instructor with date filtering and export functionality"""
    if not request.user.is_instructor():
        return HttpResponseForbidden("Only instructors can view flight history")
    
    # Set default date range (last year)
    today = date.today()
    default_start_date = today - timedelta(days=365)
    
    # Get date filters from request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Parse and validate dates
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            start_date = default_start_date
            messages.warning(request, "Invalid start date format. Using default.")
    else:
        start_date = default_start_date
    
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            end_date = today
            messages.warning(request, "Invalid end date format. Using today.")
    else:
        end_date = today
    
    # Ensure start_date is not after end_date
    if start_date > end_date:
        start_date, end_date = end_date, start_date
        messages.info(request, "Start date was after end date. Dates have been swapped.")
    
    # Get flights within the date range - EXCLUDE solo flights
    flights = TrainingRecord.objects.filter(
        instructor=request.user,
        date__gte=start_date,
        date__lte=end_date,
        is_solo=False  # Only show flights where instructor was present
    ).select_related(
        'student', 'glider'
    ).order_by('-date', '-created_at')
    
    # Get additional filters
    student_filter = request.GET.get('student')
    
    # Apply additional filters
    if student_filter:
        flights = flights.filter(student__id=student_filter)
    
    # Check for export request
    export_format = request.GET.get('export')
    if export_format in ['csv', 'pdf']:
        return _export_instructor_flights(flights, request.user, start_date, end_date, export_format)
    
    # Calculate statistics for the filtered results
    total_flights = flights.count()
    
    # Calculate total flight time
    total_duration = flights.aggregate(total=Sum('flight_duration'))['total']
    total_flight_time = "0:00"
    if total_duration:
        total_seconds = int(total_duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        total_flight_time = f"{hours}:{minutes:02d}"
    
    # Get unique students for filter dropdown - only from non-solo flights
    students_taught = User.objects.filter(
        user_type='student',
        student_records__instructor=request.user,
        student_records__is_solo=False  # Only students from instructional flights
    ).distinct().order_by('first_name', 'last_name')
    
    # Pagination
    paginator = Paginator(flights, 25)  # Show 25 flights per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'flights': page_obj,
        'all_flights': flights,  # For export count
        'start_date': start_date,
        'end_date': end_date,
        'total_flights': total_flights,
        'total_flight_time': total_flight_time,
        'students_taught': students_taught,
        'selected_student': student_filter,
        'date_range_days': (end_date - start_date).days + 1,
    }
    
    return render(request, 'training_records/instructor_flight_history.html', context)

def _export_instructor_flights(flights, instructor, start_date, end_date, format_type):
    """Export instructor flights to CSV or PDF"""
    try:
        if format_type == 'csv':
            return _export_instructor_flights_csv(flights, instructor, start_date, end_date)
        elif format_type == 'pdf':
            return _export_instructor_flights_pdf(flights, instructor, start_date, end_date)
        else:
            return HttpResponse("Invalid export format", content_type='text/plain', status=400)
    except Exception as e:
        # Log the error and return a user-friendly response
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Export error: {str(e)}")
        
        return HttpResponse(f"Export failed", content_type='text/plain', status=500)


# Update training_records/views/instructor.py
def _export_instructor_flights_csv(flights, instructor, start_date, end_date):
    """Export instructor flights to CSV"""
    response = HttpResponse(
        content_type='text/csv; charset=utf-8',
        headers={
            'Content-Disposition': f'attachment; filename="instructor_flights_{instructor.username}_{start_date}_to_{end_date}.csv"'
        },
    )
    
    # Add BOM for Excel UTF-8 recognition
    response.write('\ufeff')
    
    writer = csv.writer(response, quoting=csv.QUOTE_ALL)
    
    # Write header - add student license number
    writer.writerow([
        'Date', 'Student Name', 'Student License Number', 'Duration', 'Glider'
    ])
    
    # Write data
    for flight in flights:
        duration = str(flight.flight_duration) if flight.flight_duration else "N/A"
        glider = f"{flight.glider.tail_number} ({flight.glider.model})" if flight.glider else "N/A"
        
        # Get student license number
        student_license = flight.student.student_license_number if flight.student.student_license_number else "Not Provided"
        
        writer.writerow([
            flight.date.strftime('%Y-%m-%d') if flight.date else "N/A",
            flight.student.get_full_name(),
            student_license,
            duration,
            glider
        ])
    
    return response

def _export_instructor_flights_pdf(flights, instructor, start_date, end_date):
    """Export instructor flights to PDF using WeasyPrint"""
    if not WEASYPRINT_AVAILABLE:
        # Return an error response if WeasyPrint is not available
        response = HttpResponse("PDF export is not available. WeasyPrint is not installed.", 
                              content_type='text/plain', status=500)
        return response
    
    try:
        from django.template.loader import render_to_string
        
        # Calculate statistics
        total_flights = flights.count()
        
        total_duration = flights.aggregate(total=Sum('flight_duration'))['total']
        total_flight_time = "0:00"
        if total_duration:
            total_seconds = int(total_duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            total_flight_time = f"{hours}:{minutes:02d}"
        
        # Process flights data - add student license number
        processed_flights = []
        for flight in flights:
            duration = str(flight.flight_duration) if flight.flight_duration else "N/A"
            glider = f"{flight.glider.tail_number} ({flight.glider.model})" if flight.glider else "N/A"
            student_license = flight.student.student_license_number if flight.student.student_license_number else "Not Provided"
            
            processed_flights.append({
                'date': flight.date.strftime('%Y-%m-%d') if flight.date else "N/A",
                'student_name': flight.student.get_full_name(),
                'student_license': student_license,  # Add this new field
                'duration': duration,
                'glider': glider
            })
        
        context = {
            'instructor': instructor,
            'flights': processed_flights,
            'start_date': start_date,
            'end_date': end_date,
            'total_flights': total_flights,
            'total_flight_time': total_flight_time,
            'current_date': timezone.now().strftime('%Y-%m-%d'),
        }
        
        html_string = render_to_string('training_records/instructor_flights_pdf.html', context)
        
        html = HTML(string=html_string)
        pdf = html.write_pdf()
        
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="instructor_flights_{instructor.username}_{start_date}_to_{end_date}.pdf"'
        
        return response
        
    except Exception as e:
        # Return a proper error response
        response = HttpResponse(f"Error generating PDF", 
                              content_type='text/plain', status=500)
        return response