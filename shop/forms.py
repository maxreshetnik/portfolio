from decimal import ROUND_FLOOR, Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.forms import ModelForm, ValidationError, HiddenInput
from django.db import transaction, IntegrityError
from django.db.models import Subquery, OuterRef, F, When, Case, Sum

from .models import FILE_SIZE, IMG_SIZE, OrderItem, Order


def _check_image_size(file):
    """Checks uploaded image dimensions and a file size using
    constants from models."""
    b = 20 if FILE_SIZE[1].upper() == 'MB' else 10
    img_width, img_height = file.image.size
    if file.size > (FILE_SIZE[0] << b):
        raise ValidationError(
            'Uploaded file over {} {}.'.format(*FILE_SIZE)
        )
    if img_width < IMG_SIZE[0] or img_height < IMG_SIZE[1]:
        raise ValidationError(
            ('Image sizes are smaller than '
             '{}x{} pixels.').format(*IMG_SIZE)
        )
    return file


class CustomValidationImageFieldForm(ModelForm):
    """
    Defines an additional method for validating the image field for
    administration site forms.
    """
    def clean_image(self):
        file = self.cleaned_data['image']
        committed = getattr(file, '_committed', False)
        return file if committed or file is None else _check_image_size(file)


class CustomUserCreationForm(UserCreationForm):

    class Meta(UserCreationForm.Meta):
        model = get_user_model()

    def __init__(self, request=None, *args, **kwargs):
        """
        The 'request' parameter is set for custom create view subclass
        based on LoginView.
        The form data comes in via the standard 'data' kwarg.
        """
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            self.user_cache = user
        return user

    def get_user(self):
        return self.user_cache


class CustomUserChangeForm(UserChangeForm):

    password = None

    class Meta(UserChangeForm.Meta):
        model = get_user_model()
        fields = ('username', 'email', 'first_name', 'last_name')


class OrderForm(ModelForm):

    class Meta:
        model = Order
        fields = '__all__'

    def get_current_cost(self):
        order = self.instance
        if order.pk is None:
            return Decimal('0.00')
        price_case = Case(
            When(sale_price__gt=0, then=F('sale_price')),
            When(discount__gt=0, then=F('discount_price')),
            default=F('price'),
        )
        subquery = Subquery(OrderItem.objects.filter(
            order=order,
            specification_id=OuterRef('id')
        ).order_by().values('quantity'))
        current_cost = order.specs.annotate(
            best_price=price_case,
            item_qty=subquery,
            total_price=F('best_price') * F('item_qty'),
        ).aggregate(Sum('total_price'))['total_price__sum']
        return (current_cost.quantize(order.order_cost) if
                current_cost is not None else Decimal('0.00'))

    def reduce_available_quantity(self):
        """Reduces the available quantity of an item by the qty in order."""
        items = OrderItem.objects.select_related(
            'specification',
        ).select_for_update().filter(order=self.instance)
        try:
            with transaction.atomic():
                for item in items:
                    spec = item.specification
                    spec.available_qty = F('available_qty') - item.quantity
                    spec.save()
            return True
        except IntegrityError:
            return False

    def clean_status(self):
        """
        Defines an additional check for the uniqueness of a user order.

        Raises error if order status is changed to cart and
        cart order already exists.
        """
        status = self.cleaned_data['status']
        order = self.instance
        if order.pk is None:
            if status != order.CART:
                raise ValidationError(f'First, create an order with a '
                                      f'cart status then add products.')
        else:
            qs = self._meta.model.objects.filter(
                user=order.user, status=order.CART,
            ).exclude(pk=order.pk)
            if status == order.CART and qs.exists():
                raise ValidationError(f"User {order.user} already has "
                                      f"an order with a cart status.")
        return status

    def clean_order_cost(self):
        """Checks the total order cost on the user's page and the current value
        from the seller when the user places an order."""
        cost = self.cleaned_data['order_cost']
        if self.instance.reserved or cost == self.get_current_cost():
            return cost
        else:
            raise ValidationError(f'Some items have changed in price',
                                  code='price')

    def clean(self):
        """Defines an additional check of unique order."""
        cleaned_data = super().clean()
        if self.instance.pk is None:
            user = cleaned_data['user']
            if Order.objects.filter(user=user, status=Order.CART).exists():
                raise ValidationError(f'User {user} already has an order with '
                                      f'a cart status.', code='cart_unique')
        return cleaned_data

    def save(self, commit=True):
        """
        Saves an order and reserves items quantity.

        The reservation of all items will succeed if
        the qty each of them is available.
        """
        order = self.instance
        if order.status == order.PROCESSING and commit and not order.reserved:
            if self.reduce_available_quantity():
                order.reserved = True
            else:
                order.status = order.CART
        return super().save(commit=commit)


class PartialOrderForm(OrderForm):

    class Meta:
        model = Order
        fields = ['order_cost']


class OrderItemForm(ModelForm):

    class Meta:
        model = OrderItem
        fields = '__all__'

    def clean_quantity(self):
        qty = self.cleaned_data['quantity']
        spec = self.cleaned_data['specification']
        if qty > (av_qty := spec.available_qty):
            raise ValidationError(
                f'Only {av_qty.normalize()} left.'
            )
        if (pack_qty := spec.pre_packing) != 1:
            qty = (qty // pack_qty) * pack_qty
        else:
            qty = qty.to_integral_value(rounding=ROUND_FLOOR)
        return qty

    def get_price(self):
        spec = self.cleaned_data['specification']
        if spec.sale_price:
            price = spec.sale_price
        elif spec.discount:
            price = spec.discount_price
        else:
            price = spec.price
        return price

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.price = self.get_price()
        if commit:
            if obj.quantity > 0:
                obj = self._meta.model.objects.update_or_create(
                    order_id=obj.order_id, specification_id=obj.specification_id,
                    defaults={'quantity': obj.quantity, 'price': obj.price},
                )[0]
            else:
                self._meta.model.objects.filter(
                    order_id=obj.order_id, specification_id=obj.specification.id,
                ).delete()
        return obj


class PartialOrderItemForm(OrderItemForm):

    class Meta:
        model = OrderItem
        fields = ('specification', 'quantity')
        widgets = {'specification': HiddenInput}
