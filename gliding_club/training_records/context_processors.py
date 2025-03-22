from django.conf import settings
from django.utils.translation import get_language
from django.utils.translation import gettext as _

def club_settings(request):
    """Make club settings available to all templates."""
    return {
        'CLUB_NAME': _(settings.CLUB_NAME),
    }


def language_settings(request):
    return {
        'LANGUAGE_CODE': get_language(),
    }