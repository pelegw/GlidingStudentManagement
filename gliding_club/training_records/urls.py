# training_records/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from .views import student, instructor, training_records, exports, ground_briefings, profile, base
urlpatterns = [
    # Dashboard URLs
    path('', base.dashboard, name='dashboard'),
    path('student-dashboard/', student .student_dashboard, name='student_dashboard'),
    path('instructor-dashboard/', instructor.instructor_dashboard, name='instructor_dashboard'),
    
    # Training record URLs
    path('records/', training_records.TrainingRecordListView.as_view(), name='record_list'),
    path('records/new/', training_records.TrainingRecordCreateView.as_view(), name='record_create'),
    path('records/<int:pk>/', training_records.TrainingRecordDetailView.as_view(), name='record_detail'),
    path('records/<int:pk>/edit/', training_records.TrainingRecordUpdateView.as_view(), name='record_update'),
    
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(template_name='training_records/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # Password change URLs (including first login)
    path('change-password/', profile.change_password, name='change_password'),
    path('first-login/', profile.first_login_password_change, name='first_login'),
    
    # Profile management
    path('profile/', profile.profile_view, name='profile'),
    path('profile/update/', profile.profile_update, name='profile_update'),
    
    # Sign-off functionality
    path('records/<int:pk>/sign/', instructor.sign_record, name='sign_record'),

    #insctructor specific urls
    path('instructor/flights/', instructor.instructor_flight_history, name='instructor_flight_history'),

    path('students/lookup/', instructor.student_lookup, name='student_lookup'),
    path('students/<int:student_id>/history/', instructor.student_history, name='student_history'),
    path('students/<int:student_id>/export/<str:format>/', exports.export_student_records, name='export_student_records'),
    path('ground-briefings/', ground_briefings.GroundBriefingListView.as_view(), name='ground_briefing_list'),
    path('ground-briefings/create/', ground_briefings.GroundBriefingCreateView.as_view(), name='ground_briefing_create'),
    path('ground-briefings/<int:pk>/sign-off/', ground_briefings.ground_briefing_sign_off, name='ground_briefing_sign_off'),
    path('ground-briefings/student/', ground_briefings.student_ground_briefings, name='student_ground_briefings'),
]