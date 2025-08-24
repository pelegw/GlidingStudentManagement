# training_records/views/exports.py
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum

import os
import csv
import tempfile
import logging
from datetime import datetime
from weasyprint import HTML, CSS

from ..models import TrainingRecord, User, Exercise, ExercisePerformance, GroundBriefing

logger = logging.getLogger(__name__)

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
        elif format.lower() == 'matrix':
            return _export_exercise_matrix(student, records, request)
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
        ground_briefings = GroundBriefing.objects.filter(
            student=student,
            signed_off=True  # Only include completed briefings
        ).select_related('topic', 'instructor').order_by('topic__number')
        
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

        # Process ground briefings data for the PDF
        processed_briefings = []
        for briefing in ground_briefings:
            processed_briefings.append({
                'id': briefing.id,
                'number': briefing.topic.number,
                'topic_name': briefing.topic.name,
                'topic_details': briefing.topic.details,
                'date': briefing.date.strftime('%Y-%m-%d') if briefing.date else "N/A",
                'instructor': briefing.instructor.get_full_name() if briefing.instructor else "N/A",
                'instructor_license': briefing.instructor.instructor_license_number if briefing.instructor else "",
                'sign_off_date': briefing.sign_off_date.strftime('%Y-%m-%d') if briefing.sign_off_date else "N/A",
                'notes': briefing.notes or ""
            })
        
        # Context for the template
        context = {
            'student': student,
            'records': processed_records,
            'ground_briefings': processed_briefings,  
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

def _export_exercise_matrix(student, records, request):
    """Generate an exercise matrix PDF showing performance on each exercise across flights."""
    try:
        # Get all exercises, but sort properly by converting number to integer first
        pre_solo_exercises = list(Exercise.objects.filter(category='pre-solo'))
        post_solo_exercises = list(Exercise.objects.filter(category='post-solo'))
        
        # Custom sort function to handle numeric sorting
        def numeric_sort_key(exercise):
            try:
                if exercise.number and exercise.number.strip():
                    import re
                    match = re.search(r'(\d+)', exercise.number)
                    if match:
                        return int(match.group(1))
                    return 999
                return 999
            except (ValueError, AttributeError):
                return 999
        
        # Sort exercises numerically by their number field
        pre_solo_exercises.sort(key=numeric_sort_key)
        post_solo_exercises.sort(key=numeric_sort_key)
        
        # Check if we have data
        if not records.exists() or (not pre_solo_exercises and not post_solo_exercises):
            messages.warning(request, "No training records or exercises found to generate matrix.")
            return redirect('record_list')
        
        # Process records to extract exercise performance data
        flights = []
        
        for record in records:
            # Format duration as minutes
            if record.flight_duration:
                minutes = int(record.flight_duration.total_seconds() / 60)
                duration = f"{minutes} דקות"
            else:
                duration = "N/A"
            
            # Format date
            date_str = record.date.strftime("%d/%m/%Y") if record.date else "N/A"
            
            # Get instructor info
            if record.is_solo:
                instructor_name = "טיסת סולו"
                instructor_license = ""
            else:
                instructor_name = record.instructor.get_full_name() if record.instructor else "לא ידוע"
                instructor_license = record.instructor.instructor_license_number if record.instructor and hasattr(record.instructor, 'instructor_license_number') else ""
            
            # Create flight entry
            flight = {
                "id": record.id,
                "number": str(record.get_flight_number()),
                "date": date_str,
                "date_raw": record.date,
                "glider": f"{record.glider.tail_number}" if record.glider else "N/A",
                "duration": duration,
                "instructor_name": instructor_name,
                "instructor_license": instructor_license,
                "is_solo": record.is_solo,
                "pre_solo_exercises": [],
                "post_solo_exercises": [],
                "has_post_solo_exercises": False
            }
            
            # Get performances for all exercises
            performances = {perf.exercise_id: perf.performance 
                           for perf in ExercisePerformance.objects.filter(training_record=record)}
            
            # Map each exercise to a symbol
            for exercise in pre_solo_exercises:
                performance = performances.get(exercise.id, 'not_performed')
                
                if performance == 'performed_well':
                    symbol = "✓"
                elif performance == 'needs_improvement':
                    symbol = "⍻"
                elif performance == 'performed_badly':
                    symbol = "✗"
                else:
                    symbol = ""
                
                flight["pre_solo_exercises"].append(symbol)
            
            # Track if this flight has post-solo exercises
            has_post_solo = False
            
            for exercise in post_solo_exercises:
                performance = performances.get(exercise.id, 'not_performed')
                
                if performance == 'performed_well':
                    symbol = "✓"
                    has_post_solo = True
                elif performance == 'needs_improvement':
                    symbol = "⍻"
                    has_post_solo = True
                elif performance == 'performed_badly':
                    symbol = "✗"
                    has_post_solo = True
                else:
                    symbol = ""
                
                flight["post_solo_exercises"].append(symbol)
            
            # Flag if this flight has post-solo exercises or is a solo flight
            flight["has_post_solo_exercises"] = has_post_solo or flight["is_solo"]
            
            flights.append(flight)
        
        # Sort flights by date (ascending) to ensure consistent order
        flights.sort(key=lambda f: (f['date_raw'] or datetime.min, f['id']))
        
        # Split flights into pre-solo and post-solo lists
        pre_solo_flights = [f for f in flights if not f['has_post_solo_exercises']]
        post_solo_flights = [f for f in flights if f['has_post_solo_exercises']]
        
        # Paginate the flights - 25 flights per page
        FLIGHTS_PER_PAGE = 25
        pre_solo_pages = [pre_solo_flights[i:i+FLIGHTS_PER_PAGE] for i in range(0, len(pre_solo_flights), FLIGHTS_PER_PAGE)]
        post_solo_pages = [post_solo_flights[i:i+FLIGHTS_PER_PAGE] for i in range(0, len(post_solo_flights), FLIGHTS_PER_PAGE)]
        
        # Prepare context for the template
        context = {
            'pre_solo_pages': pre_solo_pages,
            'post_solo_pages': post_solo_pages,
            'pre_solo_exercises': pre_solo_exercises,
            'post_solo_exercises': post_solo_exercises,
            'student_name': student.get_full_name(),
            'student': student,
            'today': timezone.now().strftime("%d/%m/%Y"),
            'has_pre_solo': bool(pre_solo_pages),
            'has_post_solo': bool(post_solo_pages)
        }
        
        # Render the template
        html_content = render_to_string('training_records/exercise_matrix_paginated.html', context)
        
        # Create a temporary file to write the PDF to
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            # Generate the PDF file
            HTML(string=html_content, base_url=request.build_absolute_uri('/')).write_pdf(
                tmp.name,
                stylesheets=[
                    CSS(string="@page { size: landscape; margin: 0.5cm; }")
                ]
            )
        
        # Read the PDF file into memory and return as a response
        with open(tmp.name, 'rb') as pdf_file:
            response = HttpResponse(pdf_file.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{student.username}_exercise_matrix.pdf"'
        
        # Clean up the temporary file
        os.unlink(tmp.name)
        
        return response
    
    except Exception as e:
        # Log the error for debugging
        import traceback
        logger.error(f"Matrix export error: {str(e)}")
        logger.error(traceback.format_exc())
        raise