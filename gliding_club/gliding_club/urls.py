# gliding_club/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from . import health  

urlpatterns = [
    # Add the i18n patterns for language selection
    path('health/', health.health_check, name='health_check'),
    path('ready/', health.ready_check, name='ready_check'),
    path('i18n/', include('django.conf.urls.i18n')),
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', RedirectView.as_view(pattern_name='dashboard'), name='home'),
    path('training/', include('training_records.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)