# training_records/views/student.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.db.models import Sum
from ..models import TrainingRecord, GroundBriefing, GroundBriefingTopic
from ..forms import GroundBriefingForm
from django.utils import timezone
from datetime import timedelta

@login_required
@login_required
def student_dashboard(request):
    """Student dashboard with enhanced 8-stat layout"""
    
    # Get all training records for the user
    all_records = TrainingRecord.objects.filter(student=request.user)
    
    # Calculate 90 days ago
    ninety_days_ago = timezone.now().date() - timedelta(days=90)
    recent_records = all_records.filter(date__gte=ninety_days_ago)
    
    # All-time statistics
    total_flights = all_records.count()
    solo_flights = all_records.filter(is_solo=True).count()
    
    # Calculate total flight duration (sum of all durations)
    total_flight_duration = timedelta()
    for record in all_records:
        if record.flight_duration:
            total_flight_duration += record.flight_duration
    
    # Calculate solo flight duration
    solo_flight_duration = timedelta()
    for record in all_records.filter(is_solo=True):
        if record.flight_duration:
            solo_flight_duration += record.flight_duration
    
    # 90-day statistics
    recent_flights = recent_records.count()
    recent_solo_flights = recent_records.filter(is_solo=True).count()
    
    # Calculate recent flight duration
    recent_flight_duration = timedelta()
    for record in recent_records:
        if record.flight_duration:
            recent_flight_duration += record.flight_duration
    
    # Calculate recent solo flight duration
    recent_solo_flight_duration = timedelta()
    for record in recent_records.filter(is_solo=True):
        if record.flight_duration:
            recent_solo_flight_duration += record.flight_duration
    
    # Get additional data
    recent_training_records = all_records.order_by('-date')[:10]
    pending_records = all_records.filter(signed_off=False).order_by('-date')[:5]
    
    ground_briefings = GroundBriefing.objects.filter(student=request.user)
    pending_briefings = ground_briefings.filter(signed_off=False)
    completed_briefings = ground_briefings.filter(signed_off=True)
    
    context = {
        'title': 'Student Dashboard',
        # All-time statistics
        'total_flights': total_flights,
        'solo_flights': solo_flights,
        'total_flight_hours': total_flight_duration,  # Pass as duration object
        'solo_flight_hours': solo_flight_duration,    # Pass as duration object
        
        # 90-day statistics
        'recent_flights': recent_flights,
        'recent_solo_flights': recent_solo_flights,
        'recent_flight_hours': recent_flight_duration,      # Pass as duration object
        'recent_solo_flight_hours': recent_solo_flight_duration,  # Pass as duration object
        
        # Existing context
        'recent_training_records': recent_training_records,
        'pending_records': pending_records,
        'pending_briefings': pending_briefings,
        'completed_briefings': completed_briefings,
        'total_briefings': ground_briefings.count(),
    }
    
    return render(request, 'training_records/student_dashboard.html', context)

@login_required
def student_ground_briefings(request):
    """Dedicated page for student ground briefings"""
    if not request.user.is_student():
        return HttpResponseForbidden("Students only")
    
    # Get all the student's ground briefings
    briefings = GroundBriefing.objects.filter(
        student=request.user
    ).select_related('topic', 'instructor').order_by('topic__number')
    
    # Get all available topics for reference
    all_topics = GroundBriefingTopic.objects.all().order_by('number')
    
    # Create a lookup of topics that have briefings
    topic_status_map = {}
    for briefing in briefings:
        if briefing.topic_id not in topic_status_map:
            # If we haven't seen this topic yet, add it
            topic_status_map[briefing.topic_id] = {
                'status': 'completed' if briefing.signed_off else 'requested',
                'briefing': briefing
            }
        elif briefing.signed_off and topic_status_map[briefing.topic_id]['status'] != 'completed':
            # If we have a signed-off version of a topic, prefer that
            topic_status_map[briefing.topic_id] = {
                'status': 'completed',
                'briefing': briefing
            }
    
    # Prepare topics with their status
    topics_with_status = []
    for topic in all_topics:
        status_info = topic_status_map.get(topic.id, {'status': 'not_started', 'briefing': None})
        topics_with_status.append({
            'topic': topic,
            'status': status_info['status'],
            'briefing': status_info['briefing']
        })
    
    # Calculate completion statistics
    total_topics = all_topics.count()
    completed_briefings = briefings.filter(signed_off=True).count()
    pending_briefings = briefings.filter(signed_off=False).count()
    remaining_topics = total_topics - (completed_briefings + pending_briefings)
    
    # For the new briefing request form
    form = GroundBriefingForm(user=request.user)
    
    context = {
        'briefings': briefings,
        'topics_with_status': topics_with_status,
        'form': form,
        'stats': {
            'total': total_topics or 1,  # Prevent division by zero
            'completed': completed_briefings,
            'pending': pending_briefings,
            'remaining': remaining_topics
        }
    }
    
    return render(request, 'training_records/student_ground_briefings.html', context)