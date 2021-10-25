from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .models import Order
from .services import available_qty_handler


@receiver(pre_delete, sender=Order)
def cancel_reserved_quantity(sender, **kwargs):
    """Cancel product reservations for deleted and unshipped orders."""
    order = kwargs['instance']
    if order.status < sender.SHIPPING:
        available_qty_handler(order)
