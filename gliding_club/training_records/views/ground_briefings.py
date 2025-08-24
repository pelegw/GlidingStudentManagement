# training_records/views/ground_briefings.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import HttpResponseForbidden

from ..models import GroundBriefing, GroundBriefingTopic
from ..forms import GroundBriefingForm, GroundBriefingSignOffForm
from .base import StudentRequiredMixin

class GroundBriefingListView(LoginRequiredMixin, ListView):
    """List all ground briefings the user has access to"""
    model = GroundBriefing
    template_name = 'training_records/ground_briefing_list.html'
    context_object_name = 'briefings'
    
    def get_queryset(self):
        queryset = GroundBriefing.objects.all().select_related('topic', 'instructor', 'student')
        
        # Filter based on user type
        if self.request.user.is_student():
            queryset = queryset.filter(student=self.request.user)
        elif self.request.user.is_instructor():
            # Instructors can see briefings they signed off and pending ones
            pass  # No filter needed, they can see all
            
        return queryset.order_by('topic__number')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_student():
            # For students, add a form to request new briefings
            context['form'] = GroundBriefingForm(user=self.request.user)
        return context

class GroundBriefingCreateView(LoginRequiredMixin, StudentRequiredMixin, CreateView):
    """Create a new ground briefing request"""
    model = GroundBriefing
    form_class = GroundBriefingForm
    template_name = 'training_records/ground_briefing_form.html'
    success_url = reverse_lazy('ground_briefing_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Ensure user is passed to the form
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.student = self.request.user
        messages.success(self.request, "Ground briefing request created successfully.")
        return super().form_valid(form)

@login_required
def ground_briefing_sign_off(request, pk):
    """View to handle signing off on ground briefings"""
    if not request.user.is_instructor():
        return HttpResponseForbidden("Instructors only")
        
    briefing = get_object_or_404(GroundBriefing, pk=pk)
    
    if request.method == 'POST':
        form = GroundBriefingSignOffForm(request.POST, instance=briefing)
        if form.is_valid():
            if form.sign_off(request.user):
                messages.success(request, "Ground briefing signed off successfully.")
            else:
                messages.error(request, "Unable to sign off this briefing.")
            return redirect('instructor_dashboard')
    else:
        form = GroundBriefingSignOffForm(instance=briefing)
    
    context = {
        'form': form,
        'briefing': briefing
    }
    
    return render(request, 'training_records/ground_briefing_sign_off.html', context)

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