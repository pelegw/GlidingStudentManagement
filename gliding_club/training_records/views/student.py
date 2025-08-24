# training_records/views/student.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.db.models import Sum
from ..models import TrainingRecord, GroundBriefing, GroundBriefingTopic
from ..forms import GroundBriefingForm

@login_required
def student_dashboard(request):
    """Dashboard view for students"""
    if not request.user.is_student():
        return HttpResponseForbidden("Students only")
    
    # Get student's training records
    training_records = TrainingRecord.objects.filter(student=request.user).order_by('-date','-created_at')
    
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