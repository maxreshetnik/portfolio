from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .models import Order


@receiver(pre_delete, sender=Order)
def cancel_reserved_quantity(sender, **kwargs):
    """Cancel product reservations for deleted and unshipped orders."""
    order = kwargs['instance']
    if order.status < sender.SHIPPING and order.reserved:
        order.cancel_reserved_quantity()
