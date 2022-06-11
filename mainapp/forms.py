from django.forms import ModelForm, CharField, HiddenInput

from .services import validate_google_recaptcha
from .models import Feedback


class FeedbackForm(ModelForm):
    """Clean user feedback and validate recaptcha."""
    g_recaptcha_response = CharField(
        validators=[validate_google_recaptcha],
        widget=HiddenInput(attrs={'id': 'g-recaptcha-response'}),
        error_messages={'required': 'Please verify you are not a robot.'},
    )

    class Meta:
        model = Feedback
        fields = '__all__'
