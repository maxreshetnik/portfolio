from django.db.models.signals import pre_delete
from django.db.models import F
from django.dispatch import receiver
from .models import Order


def available_qty_handler(order):
    """Handles the available quantity of product."""
    if order.reserved:
        items = order.specs.through.objects.select_related(
            'specification',
        ).filter(order_id=order.id)
        for item in items:
            spec = item.specification
            spec.available_qty = F('available_qty') + item.quantity
            spec.save()


@receiver(pre_delete, sender=Order)
def cancel_reserved_quantity(sender, **kwargs):
    """
    Cancel a product reservation.

    If the order is canceled and not yet shipped.
    """
    order = kwargs['instance']
    if order.status < sender.SHIPPING:
        available_qty_handler(order)
