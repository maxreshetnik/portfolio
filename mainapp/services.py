import requests

from django.conf import settings
from django.core.exceptions import ValidationError


def validate_google_recaptcha(g_recaptcha_response):
    """Validate google reCAPTCHA response."""
    data = {
        'secret': getattr(settings, 'RECAPTCHA_SECRET_KEY', ''),
        'response': g_recaptcha_response
    }
    r = requests.post(
        'https://www.google.com/recaptcha/api/siteverify', data=data,
    )
    result = r.json()
    if not result['success']:
        raise ValidationError(
            "You haven't verified that you're not a robot. Try again."
        )
