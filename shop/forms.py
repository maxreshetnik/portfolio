from django.forms import ModelForm, ValidationError
from django.db.models.fields.files import ImageFieldFile

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


class ProductForm(ModelForm):

    def clean_image(self):
        file = self.cleaned_data['image']
        no_change = isinstance(file, ImageFieldFile)
        return file if no_change else check_image_size(file)


class SpecificationForm(ModelForm):

    # class Meta:
    #     model = models.Specification

    def clean_image(self):
        file = self.cleaned_data['image']
        no_change = isinstance(file, ImageFieldFile)
        return file if no_change or file is None else check_image_size(file)


class CartForm(ModelForm):

    class Meta:
        model = models.Cart
        fields = ['quantity']


class SpecCustomersForm(ModelForm):

    class Meta:
        model = models.Specification
        fields = ['customers']
