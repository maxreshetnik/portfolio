from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def decimal_normalize(d):
    """
    Normalize decimal value like cut zero ending.
    """
    return d.quantize(Decimal(1)) if d == d.to_integral() else d.normalize()
