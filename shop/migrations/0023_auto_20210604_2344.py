# Generated by Django 3.2.3 on 2021-06-04 23:44

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0022_auto_20210604_2243'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='cart',
            options={'verbose_name': 'product in cart', 'verbose_name_plural': 'cart'},
        ),
        migrations.AlterModelOptions(
            name='clothingproduct',
            options={'verbose_name': 'clothing', 'verbose_name_plural': 'clothing'},
        ),
        migrations.AlterModelOptions(
            name='foodproduct',
            options={'verbose_name': 'foodstuff'},
        ),
        migrations.AlterModelOptions(
            name='smartphoneproduct',
            options={'verbose_name': 'smartphone'},
        ),
    ]
