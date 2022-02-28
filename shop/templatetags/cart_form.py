from django import template
from django.template.loader import get_template


register = template.Library()
t_cart = get_template('shop/includes/cart_form.html')
t_list = get_template('shop/includes/cart_form_list.html')
t_detail = get_template('shop/includes/cart_form_detail.html')


def get_qty_from_dict(spec, cart, form, size='md', is_auth=False):
    qty = cart.get(spec.id, 0) if cart else 0
    return get_cart_form_context(spec, qty, form, size=size, is_auth=is_auth)


def get_cart_form_context(*args, size='md', min_qty=0, is_auth=False):
    """Returns context for inclusion template"""
    spec, qty, form = args
    step = spec.pre_packing.normalize()
    data = {'spec': spec, 'form': form, 'size': size, 'step': step,
            'is_auth': is_auth}
    if qty:
        data.update({'btn_icon': ('<i class="bi-cart-fill me-1"></i>'
                                  '<i class="bi-check-lg me-1"></i>'),
                     'btn_type': 'submit', 'btn_color': 'warning',
                     'min_qty': min_qty, 'qty': qty.normalize()})
    else:
        data.update({'qty': step, 'min_qty': step,
                     'btn_type': 'button', 'btn_color': 'primary',
                     'btn_icon': '<i class="bi-cart px-1"></i>'})

    if form.is_bound and form['specification'].data == str(spec.id):
        data['non_field_errors'] = ', '.join(form.non_field_errors())
        data['quantity_errors'] = ', '.join(form['quantity'].errors)
        data['is_invalid'] = 'is-invalid'
    return data


register.inclusion_tag(t_cart, name='get_cart_form')(get_cart_form_context)
register.inclusion_tag(t_list, name='get_cart_form_list')(get_qty_from_dict)
register.inclusion_tag(
    t_detail, name='get_cart_form_detail'
)(get_qty_from_dict)
