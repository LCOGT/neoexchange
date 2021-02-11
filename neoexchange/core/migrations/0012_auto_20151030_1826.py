# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_merge'),
    ]

    operations = [
        migrations.AddField(
            model_name='sourcemeasurement',
            name='aperture_size',
            field=models.FloatField(null=True, verbose_name=b'Size of aperture (arcsec)', blank=True),
        ),
        migrations.AddField(
            model_name='sourcemeasurement',
            name='astrometric_catalog',
            field=models.CharField(default=b' ', max_length=40, verbose_name=b'Astrometric catalog used'),
        ),
        migrations.AddField(
            model_name='sourcemeasurement',
            name='flags',
            field=models.CharField(default=b' ', help_text=b'Comma separated list of frame/condition flags', max_length=40, verbose_name=b'Frame Quality flags', blank=True),
        ),
        migrations.AddField(
            model_name='sourcemeasurement',
            name='frame',
            field=models.ForeignKey(to='core.Frame', on_delete=models.deletion.CASCADE),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='sourcemeasurement',
            name='photometric_catalog',
            field=models.CharField(default=b' ', max_length=40, verbose_name=b'Photometric catalog used'),
        ),
        migrations.AddField(
            model_name='sourcemeasurement',
            name='snr',
            field=models.FloatField(null=True, verbose_name=b'Size of aperture (arcsec)', blank=True),
        ),
    ]
