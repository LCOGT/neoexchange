# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-07-09 19:02
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0038_auto_20180703_0505'),
    ]

    operations = [
        migrations.CreateModel(
            name='StaticSource',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=55, verbose_name='Name of calibration source')),
                ('ra', models.FloatField(verbose_name='RA of source (degrees)')),
                ('dec', models.FloatField(verbose_name='Dec of source (degrees)')),
                ('pm_ra', models.FloatField(default=0.0, verbose_name='Proper motion in RA of source (pmra*cos(dec); mas/yr)')),
                ('pm_dec', models.FloatField(default=0.0, verbose_name='Proper motion in Dec of source (mas/yr)')),
                ('parallax', models.FloatField(default=0.0, verbose_name='Parallax (mas)')),
                ('vmag', models.FloatField(verbose_name='V magnitude')),
                ('spectral_type', models.CharField(blank=True, max_length=10, verbose_name='Spectral type of source')),
                ('source_type', models.IntegerField(choices=[(0, 'Unknown source type'), (1, 'Spectrophotometric standard'), (2, 'Radial velocity standard'), (4, 'Solar spectrum standard'), (8, 'Spectral standard')], default=0, verbose_name='Source Type')),
                ('notes', models.TextField(blank=True)),
                ('quality', models.SmallIntegerField(blank=True, default=0, null=True, verbose_name='Source quality')),
                ('reference', models.CharField(blank=True, max_length=255, verbose_name='Reference for the source')),
            ],
            options={
                'verbose_name': 'Static Source',
                'verbose_name_plural': 'Static Sources',
                'db_table': 'ingest_staticsource',
            },
        ),
    ]
