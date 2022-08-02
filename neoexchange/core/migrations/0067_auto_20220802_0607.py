# Generated by Django 3.1.14 on 2022-08-02 06:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0066_auto_20220801_1532'),
    ]

    operations = [
        migrations.AddField(
            model_name='frame',
            name='color',
            field=models.FloatField(blank=True, null=True, verbose_name='Color coefficient (mag.)'),
        ),
        migrations.AddField(
            model_name='frame',
            name='color_err',
            field=models.FloatField(blank=True, null=True, verbose_name='Error on color coefficient (mag.)'),
        ),
        migrations.AddField(
            model_name='frame',
            name='color_used',
            field=models.CharField(blank=True, default='', max_length=15, null=True, verbose_name='Color used for calibration'),
        ),
        migrations.AddField(
            model_name='frame',
            name='zeropoint_src',
            field=models.TextField(blank=True, null=True, verbose_name='Source of Frame zeropoint'),
        ),
        migrations.AlterField(
            model_name='frame',
            name='frametype',
            field=models.SmallIntegerField(choices=[(0, 'Single frame'), (1, 'Stack of frames'), (2, 'Non-LCOGT data'), (3, 'Satellite data'), (4, 'Spectrum'), (5, 'FITS LDAC catalog'), (6, 'BANZAI LDAC catalog'), (10, 'ORACDR QL frame'), (11, 'BANZAI QL frame'), (80, 'Reference frame'), (90, 'ORACDR reduced frame'), (91, 'BANZAI reduced frame'), (92, 'NEOexchange reduced frame'), (93, 'NEOexchange DIA subtracted frame')], default=0, verbose_name='Frame Type'),
        ),
    ]
