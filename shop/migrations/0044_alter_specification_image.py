# Generated by Django 3.2.3 on 2021-07-13 19:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0043_auto_20210713_1851'),
    ]

    operations = [
        migrations.AlterField(
            model_name='specification',
            name='image',
            field=models.ImageField(blank=True, default='', help_text='Minimal image sizes is 400x400 pixels. Max upload file size up to 10 MB.', upload_to='shop/'),
            preserve_default=False,
        ),
    ]
