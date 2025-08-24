# training_records/views/base.py
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponseForbidden

class StudentRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_student()

class InstructorRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_instructor()

@login_required
def dashboard(request):
    """Main dashboard that redirects to the appropriate view based on user type"""
    if request.user.is_instructor():
        return redirect('instructor_dashboard')
    elif request.user.is_student():
        return redirect('student_dashboard')
    else:
        return redirect('admin:index')  # Fallback to admin