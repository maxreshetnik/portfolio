# Generated by Django 3.2.3 on 2021-06-20 22:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0034_auto_20210620_2037'),
    ]

    operations = [
        migrations.AddField(
            model_name='specification',
            name='sale_price',
            field=models.DecimalField(decimal_places=2, default='0', help_text='Special sale price (optional)', max_digits=9),
        ),
    ]