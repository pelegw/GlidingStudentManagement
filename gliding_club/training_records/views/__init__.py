# training_records/views/__init__.py
"""
Training Records Views

Organized by functionality:
- base: Common mixins and main dashboard redirector
- student: Student-specific views  
- instructor: Instructor-specific views
- training_records: CRUD operations for training records
- profile: Profile and authentication views
- exports: Export functionality (PDF, CSV, Matrix)
- ground_briefings: Ground briefing management
"""

# Import all views to maintain backward compatibility
from .base import (
    StudentRequiredMixin,
    InstructorRequiredMixin, 
    dashboard
)

from .student import (
    student_dashboard,
    
)

from .instructor import (
    instructor_dashboard,
    sign_record,
    student_history,
    student_lookup,
    instructor_flight_history,
    
)

from .training_records import (
    TrainingRecordListView,
    TrainingRecordDetailView,
    TrainingRecordCreateView,
    TrainingRecordUpdateView
)

from .profile import (
    profile_view,
    profile_update,
    change_password,
    first_login_password_change
)

from .exports import (
    export_student_records
)

from .ground_briefings import (
    GroundBriefingListView,
    GroundBriefingCreateView,
    ground_briefing_sign_off,
    student_ground_briefings
)

# This allows existing imports to continue working
__all__ = [
    'StudentRequiredMixin',
    'InstructorRequiredMixin',
    'dashboard',
    'student_dashboard', 
    'instructor_dashboard',
    'sign_record',
    'student_history',
    'student_lookup',
    'TrainingRecordListView',
    'TrainingRecordDetailView', 
    'TrainingRecordCreateView',
    'TrainingRecordUpdateView',
    'profile_view',
    'profile_update',
    'change_password',
    'first_login_password_change',
    'export_student_records',
    'ground_briefing_sign_off',
    'student_ground_briefings',
    'GroundBriefingListView',
    'GroundBriefingCreateView'
    'instructor_flight_history',
]