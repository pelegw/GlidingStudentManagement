# training_records/views/training_records.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect
from django.db.models import Q
from django.db import transaction
import logging

from ..models import TrainingRecord, Exercise, ExercisePerformance
from ..forms import TrainingRecordForm
from .base import StudentRequiredMixin

logger = logging.getLogger(__name__)

class TrainingRecordListView(LoginRequiredMixin, ListView):
    """List all training records the user has access to"""
    model = TrainingRecord
    template_name = 'training_records/record_list.html'
    context_object_name = 'records'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = TrainingRecord.objects.all().order_by('-date','-created_at')
        
        # Filter based on user type
        if self.request.user.is_student():
            queryset = queryset.filter(student=self.request.user)
        elif self.request.user.is_instructor():
            # Instructors can see all flights
            queryset = queryset.filter(
                
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

        # Check if any performed exercises exist (not just 'not_performed')
        performed_exercises_exist = self.object.exercise_performances.filter(
            performance__in=['performed_well', 'needs_improvement','performed_badly']
        ).exists()
        context['performed_exercises_exist'] = performed_exercises_exist

        # Get exercise performances grouped by category - only include performed ones
        context['pre_solo_performances'] = self.object.exercise_performances.filter(
            exercise__category='pre-solo',
            performance__in=['performed_well', 'needs_improvement', 'performed_badly']
        ).select_related('exercise').order_by('exercise__number', 'exercise__name')
        
        context['post_solo_performances'] = self.object.exercise_performances.filter(
            exercise__category='post-solo',
            performance__in=['performed_well', 'needs_improvement', 'performed_badly']
        ).select_related('exercise').order_by('exercise__number', 'exercise__name')

        return context

class TrainingRecordCreateView(LoginRequiredMixin, CreateView):
    """Create a new training record with exercise performances"""
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
        
        # Add exercise categories for display
        context['pre_solo_exercises'] = Exercise.objects.filter(category='pre-solo').order_by('number', 'name')
        context['post_solo_exercises'] = Exercise.objects.filter(category='post-solo').order_by('number', 'name')
        
        return context
    
    def form_valid(self, form):
        # Set the student to the current user if they're a student
        if self.request.user.is_student():
            form.instance.student = self.request.user
        
        # Process the main form and get the TrainingRecord instance
        self.object = form.save()
        
        # Get all exercises to ensure we have a performance record for each
        all_exercises = Exercise.objects.all()
        processed_exercise_ids = set()
        
        # Process the exercise performance data from the POST request
        if self.request.POST:
            total_forms = int(self.request.POST.get('form-TOTAL_FORMS', 0))
            
            for i in range(total_forms):
                prefix = f'form-{i}'
                exercise_id = self.request.POST.get(f'{prefix}-exercise')
                performance = self.request.POST.get(f'{prefix}-performance')
                notes = self.request.POST.get(f'{prefix}-notes', '')
                
                if exercise_id and performance:
                    try:
                        exercise_id = int(exercise_id)
                        processed_exercise_ids.add(exercise_id)
                        exercise = Exercise.objects.get(pk=exercise_id)
                        
                        # Create the performance record
                        ExercisePerformance.objects.create(
                            training_record=self.object,
                            exercise=exercise,
                            performance=performance,
                            notes=''
                        )
                    except (Exercise.DoesNotExist, ValueError) as e:
                        # Log an error but continue processing
                        logger.error(f"Error processing exercise {exercise_id}: {str(e)}")
                        print(f"Error processing exercise {exercise_id}: {str(e)}")
        
        # For any exercises not processed (not in the form), create a default 'not_performed' record
        for exercise in all_exercises:
            if exercise.id not in processed_exercise_ids:
                ExercisePerformance.objects.create(
                    training_record=self.object,
                    exercise=exercise,
                    performance='not_performed',
                    notes=''
                )
        
        messages.success(self.request, 'Training record created successfully.')
        return redirect(self.get_success_url())

class TrainingRecordUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing training record with exercise performances"""
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
        
        # Debug output
        print("======= DEBUG: TrainingRecordUpdateView.get_context_data =======")
        print(f"Record ID: {self.object.id}")
        
        # Add exercise categories for display
        pre_solo_exercises = Exercise.objects.filter(category='pre-solo').order_by('number', 'name')
        post_solo_exercises = Exercise.objects.filter(category='post-solo').order_by('number', 'name')
        
        # Debug output for exercises
        print(f"Pre-solo exercises: {pre_solo_exercises.count()}")
        print(f"Post-solo exercises: {post_solo_exercises.count()}")
        
        for ex in pre_solo_exercises[:3]:  # Print first 3 for debugging
            print(f"Pre-solo example: {ex.id} - {ex.name}")
        
        context['pre_solo_exercises'] = pre_solo_exercises
        context['post_solo_exercises'] = post_solo_exercises
        
        # Get existing performances to mark as selected in the template
        existing_performances = {}
        perf_count = 0
        for perf in self.object.exercise_performances.all():
            existing_performances[perf.exercise_id] = {
                'performance': perf.performance,
                'notes': perf.notes
            }
            perf_count += 1
            if perf_count <= 3:  # Print first 3 for debugging
                print(f"Performance: Exercise {perf.exercise_id} - {perf.performance}")
        
        # Debug output for performances
        print(f"Total performances found: {perf_count}")
        
        context['existing_performances'] = existing_performances
        
        # Add counts to context for debugging in template
        context['pre_solo_count'] = pre_solo_exercises.count()
        context['post_solo_count'] = post_solo_exercises.count()
        context['performance_count'] = perf_count
        
        print("============= END DEBUG =============")
        
        return context
    
    def form_valid(self, form):
        # Save the main form first to get/update the TrainingRecord instance
        self.object = form.save()
        
        print("======= DEBUG: TrainingRecordUpdateView.form_valid =======")
        print(f"Processing form for Record ID: {self.object.id}")
        
        # Check if the form includes exercise-related data
        has_exercise_data = False
        exercise_fields = []
        exercise_ids = []
        
        for key in self.request.POST:
            if '-exercise' in key:
                has_exercise_data = True
                exercise_fields.append(key)
                try:
                    exercise_id = self.request.POST.get(key)
                    if exercise_id:
                        exercise_ids.append(int(exercise_id))
                except (ValueError, TypeError):
                    pass
        
        print(f"Exercise fields found: {len(exercise_fields)}")
        print(f"Exercise IDs found: {len(exercise_ids)}")
        
        # Only process exercises if we have exercise data
        if has_exercise_data:
            # Track processed exercises
            processed_exercise_ids = set()
            
            # Process form data for exercises
            total_forms = int(self.request.POST.get('form-TOTAL_FORMS', 0))
            print(f"TOTAL_FORMS value: {total_forms}")
            
            for i in range(total_forms):
                prefix = f'form-{i}'
                exercise_id = self.request.POST.get(f'{prefix}-exercise')
                performance = self.request.POST.get(f'{prefix}-performance')
                #notes = self.request.POST.get(f'{prefix}-notes', '')
                
                if i < 5:  # First 5 for debugging
                    print(f"Form data {i}: Exercise={exercise_id}, Performance={performance}")
                
                if exercise_id and performance:
                    try:
                        exercise_id = int(exercise_id)
                        exercise = Exercise.objects.get(pk=exercise_id)
                        processed_exercise_ids.add(exercise_id)
                        
                        # Update or create performance record
                        obj, created = ExercisePerformance.objects.update_or_create(
                            training_record=self.object,
                            exercise=exercise,
                            defaults={
                                'performance': performance,
                                'notes': ''
                            }
                        )
                        
                        if i < 5:  # First 5 for debugging
                            print(f"Processed: {exercise.name} - {performance} - {'created' if created else 'updated'}")
                            
                    except (Exercise.DoesNotExist, ValueError, TypeError) as e:
                        # Log error but continue processing
                        print(f"Error processing exercise {exercise_id}: {str(e)}")
            
            print(f"Total exercises processed: {len(processed_exercise_ids)}")
            
            # If no exercises were processed but we had exercise_ids in the form,
            # something might have gone wrong with the form processing
            if not processed_exercise_ids and exercise_ids:
                print(f"WARNING: No exercises processed despite having IDs in form: {exercise_ids}")
        else:
            print("No exercise data found in the form submission")
        
        print("============= END DEBUG =============")
        
        messages.success(self.request, 'Training record updated successfully.')
        return redirect(self.get_success_url())
    
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
    