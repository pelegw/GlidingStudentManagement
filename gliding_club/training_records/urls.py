# training_records/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Dashboard URLs
    path('', views.dashboard, name='dashboard'),
    path('student-dashboard/', views.student_dashboard, name='student_dashboard'),
    path('instructor-dashboard/', views.instructor_dashboard, name='instructor_dashboard'),
    
    # Training record URLs
    path('records/', views.TrainingRecordListView.as_view(), name='record_list'),
    path('records/new/', views.TrainingRecordCreateView.as_view(), name='record_create'),
    path('records/<int:pk>/', views.TrainingRecordDetailView.as_view(), name='record_detail'),
    path('records/<int:pk>/edit/', views.TrainingRecordUpdateView.as_view(), name='record_update'),
    
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(template_name='training_records/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # Password change URLs (including first login)
    path('change-password/', views.change_password, name='change_password'),
    path('first-login/', views.first_login_password_change, name='first_login'),
    
    # Profile management
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.profile_update, name='profile_update'),
    
    # Sign-off functionality
    path('records/<int:pk>/sign/', views.sign_record, name='sign_record'),


    path('students/lookup/', views.student_lookup, name='student_lookup'),
    path('students/<int:student_id>/history/', views.student_history, name='student_history'),

    path('students/<int:student_id>/export/<str:format>/', views.export_student_records, name='export_student_records'),

    path('ground-briefings/', views.GroundBriefingListView.as_view(), name='ground_briefing_list'),
    path('ground-briefings/create/', views.GroundBriefingCreateView.as_view(), name='ground_briefing_create'),
    path('ground-briefings/<int:pk>/sign-off/', views.ground_briefing_sign_off, name='ground_briefing_sign_off'),
    path('ground-briefings/student/', views.student_ground_briefings, name='student_ground_briefings'),
]