# training_records/templatetags/time_filters.py
from django import template

register = template.Library()

@register.filter
def duration_format(duration):
    """Format a duration object to HH:MM"""
    if not duration:
        return "0:00"
    
    total_seconds = int(duration.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    
    return f"{hours}:{minutes:02d}"