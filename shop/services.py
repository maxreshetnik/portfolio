from io import BytesIO
from PIL import Image

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.files.images import ImageFile, File


IMG_SIZE = (600, 600)   # minimal image sizes in pixels
FILE_SIZE = (3, 'MB')   # maximal file size 'MB' or 'KB' only


def get_file_directory_path(instance, filename):
    ct_obj = ContentType.objects.get_for_model(instance)
    return f'{ct_obj.app_label}/{filename}'


def handle_image_size(obj):
    """
    Changes dimensions of an image to the dimensions in IMG_SIZE constant.

    If an image is loaded and the image size is not equal to the IMG_SIZE,
    the function creates new image object and replaces old one.
    """
    if (getattr(obj, '_committed', True) or not obj.name or
            (obj.width, obj.height) == IMG_SIZE):
        return
    try:
        with obj.open(), Image.open(obj) as img:
            new_img = img.resize(IMG_SIZE, reducing_gap=3.0)
            file = getattr(obj, 'file')
            name = obj.name if not isinstance(file, File) else (
                str(obj.name).rpartition('/')[2])
            new_file = ImageFile(BytesIO(), name)
            new_img.save(new_file, img.format)
    except OSError:
        return
    setattr(obj, 'file', new_file)
    setattr(obj, 'name', name)


def validate_image_size(file):
    """Validate that image dimensions and file size match
    the values in constants."""
    if not getattr(file, '_committed', True):
        b = 20 if FILE_SIZE[1].upper() == 'MB' else 10
        if file.size > (FILE_SIZE[0] << b):
            raise ValidationError(f'The uploaded file is larger than '
                                  f'{FILE_SIZE[0]} {FILE_SIZE[1]}.')
        if file.width < IMG_SIZE[0] or file.height < IMG_SIZE[1]:
            raise ValidationError(f'Image sizes are smaller than '
                                  f'{IMG_SIZE[0]}x{IMG_SIZE[1]} pixels.')
