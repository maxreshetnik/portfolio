# Generated by Django 3.2.3 on 2021-07-27 22:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0045_auto_20210727_2038'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='cart',
            constraint=models.UniqueConstraint(fields=('specification', 'user'), name='user_item_unique'),
        ),
    ]
