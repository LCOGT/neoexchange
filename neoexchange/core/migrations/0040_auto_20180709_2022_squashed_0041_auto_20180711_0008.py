# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-07-11 00:09
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    replaces = [('core', '0040_auto_20180709_2022'), ('core', '0041_auto_20180711_0008')]

    dependencies = [
        ('core', '0039_staticsource'),
    ]

    operations = [
        migrations.AddField(
            model_name='block',
            name='calibsource',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.StaticSource'),
        ),
        migrations.AlterField(
            model_name='block',
            name='body',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.Body'),
        ),
        migrations.AlterField(
            model_name='block',
            name='obstype',
            field=models.SmallIntegerField(choices=[(0, 'Optical imaging'), (1, 'Optical spectra'), (2, 'Optical imaging calibration'), (3, 'Optical spectro calibration')], default=0, verbose_name='Observation Type'),
        ),
    ]
