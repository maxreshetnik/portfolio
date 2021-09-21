# Generated by Django 3.2.3 on 2021-09-20 18:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0058_shippingaddress_unique_default_address'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.PositiveIntegerField(choices=[(1, 'Cart'), (2, 'Processing'), (3, 'Shipping'), (4, 'Finished'), (5, 'Canceled')]),
        ),
    ]
