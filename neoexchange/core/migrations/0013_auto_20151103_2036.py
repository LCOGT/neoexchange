# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_auto_20151030_1826'),
    ]

    operations = [
        migrations.AlterField(
            model_name='frame',
            name='filter',
            field=models.CharField(default=b'B', max_length=15, verbose_name=b'filter class'),
        ),
        migrations.AlterField(
            model_name='frame',
            name='sitecode',
            field=models.CharField(default=None, max_length=4, verbose_name=b'MPC site code'),
        ),
        migrations.AlterField(
            model_name='sourcemeasurement',
            name='obs_mag',
            field=models.FloatField(null=True, verbose_name=b'Observed Magnitude', blank=True),
        ),
    ]
