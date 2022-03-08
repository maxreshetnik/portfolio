from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail

from .models import Feedback


@receiver(post_save, sender=Feedback, weak=False,
          dispatch_uid="forward_feedback_msg")
def forward_feedback_msg(sender, **kwargs):
    if kwargs['created']:
        feedback = kwargs['instance']
        send_mail(
            f'Feedback from {feedback.name}',
            (f'{feedback.message}\n\nName: {feedback.name}\n'
             f'email: {feedback.email}'),
            feedback.email,
            [feedback.portfolio.email],
            fail_silently=True,
        )
    return sender
