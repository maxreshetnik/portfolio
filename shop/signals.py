from django.db.models.signals import pre_delete
from django.db.models import F
from django.dispatch import receiver
from .models import Order


@receiver(pre_delete, sender=Order)
def available_qty_handler(sender, **kwargs):
    """
    Handles the available quantity of product.

    If the order is canceled and not yet shipped.
    """
    order = kwargs['instance']
    if order.status < sender.SHIPPING and order.reserved:
        items = order.specs.through.objects.select_related(
            'specification',
        ).filter(order_id=order.id)
        for item in items:
            spec = item.specification
            spec.available_qty = F('available_qty') + item.quantity
            spec.save()
