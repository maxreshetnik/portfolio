from django.conf import settings
from django.db.models import ImageField, FileField, Q
from django.contrib.contenttypes.models import ContentType


def move_media(*names, back=False):

    old, new = ('temp', '') if back else ('', 'temp')
    media_root = settings.MEDIA_ROOT
    for name in names:
        old_path = media_root.joinpath(old, name)
        if old_path.is_file():
            new_path = media_root.joinpath(new, name)
            try:
                old_path.rename(new_path)
            except FileNotFoundError:
                new_path.parent.mkdir(parents=True)
                old_path.rename(new_path)
            # print(new_path)
            # print(new_path.parent, '----', new_path.name)
            # print(val)


def get_filefield_values(*ct_id):

    query_list = []
    for i in ct_id:
        model = ContentType.objects.get_for_id(i).model_class()
        opts = getattr(model, '_meta')
        fields = [f.attname for f in opts.get_fields() if (
            isinstance(f, (ImageField, FileField)))]
        if fields:
            query_list.append(model.objects.values_list(*fields))
    return query_list


def clean_media(*ct_id, dir_name=None):

    media_root = settings.MEDIA_ROOT
    deleted_path = media_root.joinpath('deleted')
    query_list = get_filefield_values(*ct_id)
    for queryset in query_list:
        for names in queryset:
            move_media(*names)
    if dir_name is None:
        return
    if not deleted_path.is_dir():
        deleted_path.mkdir()
    for file in media_root.joinpath(dir_name).iterdir():
        if file.is_file:
            file.rename(deleted_path.joinpath(file.name))
    for queryset in query_list:
        for names in queryset:
            move_media(*names, back=True)


def clean_shop_media():

    ct_id = ContentType.objects.filter(
        Q(model__endswith='product') | Q(model='specification'),
    ).values_list('id', flat=True)
    clean_media(*ct_id, dir_name='shop')
