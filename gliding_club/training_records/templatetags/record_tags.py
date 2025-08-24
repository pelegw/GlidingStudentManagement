from django import template

register = template.Library()

@register.filter
def is_modifiable_by(record, user):
    """Check if a record is modifiable by the given user"""
    if hasattr(record, 'is_modifiable_by_instructor'):
        return record.is_modifiable_by_instructor(user)
    return False

@register.filter  
def days_until_deadline(record):
    """Get days until modification deadline"""
    if hasattr(record, 'days_until_modification_deadline'):
        return record.days_until_modification_deadline()
    return None