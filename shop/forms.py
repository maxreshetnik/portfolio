from decimal import Decimal, ROUND_FLOOR

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.forms import (ModelForm, Form, ValidationError, DecimalField,
                          ModelChoiceField, HiddenInput)

from . import models


def check_image_size(file):
    b = 20 if models.FILE_SIZE[1].upper() == 'MB' else 10
    img_width, img_height = file.image.size
    if file.size > (models.FILE_SIZE[0] << b):
        raise ValidationError(
            'Uploaded file over {} {}.'.format(*models.FILE_SIZE)
        )
    if img_width < models.IMG_SIZE[0] or img_height < models.IMG_SIZE[1]:
        raise ValidationError(
            ('Image sizes are smaller than '
             '{}x{} pixels.').format(*models.IMG_SIZE)
        )
    return file


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


class ProductForm(ModelForm):

    def clean_image(self):
        file = self.cleaned_data['image']
        committed = getattr(file, '_committed', False)
        return file if committed else check_image_size(file)


class SpecificationForm(ModelForm):

    def clean_image(self):
        file = self.cleaned_data['image']
        committed = getattr(file, '_committed', False)
        return file if committed or file is None else check_image_size(file)


class CartItemForm(Form):

    specification = ModelChoiceField(
        queryset=models.Specification.objects.all(),
        widget=HiddenInput, required=True,
    )
    quantity = DecimalField(max_digits=8, decimal_places=3,
                            min_value=Decimal('0'))

    def clean_quantity(self):
        qty = self.cleaned_data['quantity']
        if qty > (av_qty := self.cleaned_data['specification'].available_qty):
            raise ValidationError(
                f'Only {av_qty.normalize()} left.'
            )
        if (pack_qty := self.cleaned_data['specification'].pre_packing) != 1:
            qty = (qty // pack_qty) * pack_qty
        else:
            qty = qty.to_integral_value(rounding=ROUND_FLOOR)
        return qty


# class SpecCustomersForm(ModelForm):
#
#     class Meta:
#         model = models.Specification
#         fields = ['customers']
