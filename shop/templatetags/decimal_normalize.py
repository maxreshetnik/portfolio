from django import template

register = template.Library()


@register.filter
def decimal_normalize(value):
    """
    Normalize decimal value like cut zero ending.
    """
    return value.normalize()
