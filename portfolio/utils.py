from pathlib import Path

from django.conf import settings
from django.db.models import ImageField, FileField, Q
from django.contrib.contenttypes.models import ContentType


def move_media(*names, back=False):
    """Moves media files to or from a temporary directory."""
    old, new = ('temp', '') if back else ('', 'temp')
    media_root = Path(settings.MEDIA_ROOT)
    for name in names:
        old_path = media_root.joinpath(old, name)
        if old_path.is_file():
            new_path = media_root.joinpath(new, name)
            try:
                old_path.rename(new_path)
            except FileNotFoundError:
                new_path.parent.mkdir(parents=True)
                old_path.rename(new_path)


def get_filefield_values(*ct_id):
    """Returns a list that contain queryset with values of the file fields."""
    queryset_list = []
    for i in ct_id:
        model = ContentType.objects.get_for_id(i).model_class()
        opts = getattr(model, '_meta')
        fields = [f.attname for f in opts.get_fields() if (
            isinstance(f, (ImageField, FileField)))]
        if fields:
            queryset_list.append(model.objects.values_list(*fields))
    return queryset_list


def clean_media(*ct_id, dir_name=None):
    """
    Cleans up media files whose names are not in a database.

    Accepts content type id and directory for cleaning,
    if the files are not in the database, they are moved to a deleted dir.
    If the directory is not specified, the files existing in
    the database are moved to a temp.
    """
    media_root = Path(settings.MEDIA_ROOT)
    deleted_path = media_root.joinpath('deleted')
    queryset_list = get_filefield_values(*ct_id)
    for queryset in queryset_list:
        for names in queryset:
            move_media(*names)
    if dir_name is None:
        return
    if not deleted_path.is_dir():
        deleted_path.mkdir()
    for file in media_root.joinpath(dir_name).iterdir():
        if file.is_file:
            file.rename(deleted_path.joinpath(file.name))
    for queryset in queryset_list:
        for names in queryset:
            move_media(*names, back=True)


def clean_shop_media():
    """Cleans up shop media files"""
    ct_id = ContentType.objects.filter(
        Q(model__endswith='product') | Q(model='specification'),
    ).values_list('id', flat=True)
    clean_media(*ct_id, dir_name='shop')
