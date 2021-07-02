# Generated by Django 3.2.3 on 2021-06-04 20:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0018_rename_content_id_rate_object_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='clothingproduct',
            name='unit',
            field=models.CharField(choices=[('Weight', (('KG', 'kg.'), ('LB', 'lb.'))), ('Volume', (('L', 'L.'), ('GL', 'gal.'))), ('PC', 'piece'), ('PK', 'pack'), ('PR', 'pair'), ('BL', 'bottle'), ('LT', 'lot')], default='PC', max_length=2),
        ),
        migrations.AlterField(
            model_name='clothingproduct',
            name='unit_for_weight_vol',
            field=models.CharField(choices=[('Weight', (('KG', 'kg.'), ('LB', 'lb.'))), ('Volume', (('L', 'L.'), ('GL', 'gal.'))), ('PC', 'piece'), ('PK', 'pack'), ('PR', 'pair'), ('BL', 'bottle'), ('LT', 'lot')], default='KG', max_length=2, verbose_name='unit for weight / vol.'),
        ),
        migrations.AlterField(
            model_name='foodproduct',
            name='unit',
            field=models.CharField(choices=[('Weight', (('KG', 'kg.'), ('LB', 'lb.'))), ('Volume', (('L', 'L.'), ('GL', 'gal.'))), ('PC', 'piece'), ('PK', 'pack'), ('PR', 'pair'), ('BL', 'bottle'), ('LT', 'lot')], default='PC', max_length=2),
        ),
        migrations.AlterField(
            model_name='foodproduct',
            name='unit_for_weight_vol',
            field=models.CharField(choices=[('Weight', (('KG', 'kg.'), ('LB', 'lb.'))), ('Volume', (('L', 'L.'), ('GL', 'gal.'))), ('PC', 'piece'), ('PK', 'pack'), ('PR', 'pair'), ('BL', 'bottle'), ('LT', 'lot')], default='KG', max_length=2, verbose_name='unit for weight / vol.'),
        ),
        migrations.AlterField(
            model_name='smartphoneproduct',
            name='unit',
            field=models.CharField(choices=[('Weight', (('KG', 'kg.'), ('LB', 'lb.'))), ('Volume', (('L', 'L.'), ('GL', 'gal.'))), ('PC', 'piece'), ('PK', 'pack'), ('PR', 'pair'), ('BL', 'bottle'), ('LT', 'lot')], default='PC', max_length=2),
        ),
        migrations.AlterField(
            model_name='smartphoneproduct',
            name='unit_for_weight_vol',
            field=models.CharField(choices=[('Weight', (('KG', 'kg.'), ('LB', 'lb.'))), ('Volume', (('L', 'L.'), ('GL', 'gal.'))), ('PC', 'piece'), ('PK', 'pack'), ('PR', 'pair'), ('BL', 'bottle'), ('LT', 'lot')], default='KG', max_length=2, verbose_name='unit for weight / vol.'),
        ),
        migrations.AlterField(
            model_name='tvproduct',
            name='unit',
            field=models.CharField(choices=[('Weight', (('KG', 'kg.'), ('LB', 'lb.'))), ('Volume', (('L', 'L.'), ('GL', 'gal.'))), ('PC', 'piece'), ('PK', 'pack'), ('PR', 'pair'), ('BL', 'bottle'), ('LT', 'lot')], default='PC', max_length=2),
        ),
        migrations.AlterField(
            model_name='tvproduct',
            name='unit_for_weight_vol',
            field=models.CharField(choices=[('Weight', (('KG', 'kg.'), ('LB', 'lb.'))), ('Volume', (('L', 'L.'), ('GL', 'gal.'))), ('PC', 'piece'), ('PK', 'pack'), ('PR', 'pair'), ('BL', 'bottle'), ('LT', 'lot')], default='KG', max_length=2, verbose_name='unit for weight / vol.'),
        ),
    ]