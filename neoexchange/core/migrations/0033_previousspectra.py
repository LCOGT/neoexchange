# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2017-12-18 19:36
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0032_auto_20171115_1856'),
    ]

    operations = [
        migrations.CreateModel(
            name='PreviousSpectra',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('spec_wav', models.CharField(blank=True, choices=[(b'Vis', b'Visible'), (b'NIR', b'Near Infrared'), (b'VIS+NIR', b'Both Visible and Near IR'), (b'NA', b'None Yet.')], max_length=7, null=True, verbose_name=b'Wavelength')),
                ('spec_vis', models.CharField(blank=True, max_length=25, null=True, verbose_name=b'Visible Spectra Link')),
                ('spec_ir', models.CharField(blank=True, max_length=25, null=True, verbose_name=b'IR Spectra Link')),
                ('spec_ref', models.CharField(blank=True, max_length=10, null=True, verbose_name=b'Spectra Reference')),
                ('spec_source', models.CharField(blank=True, choices=[(b'S', b'SMASS'), (b'M', b'MANOS')], max_length=1, null=True, verbose_name=b'Source')),
                ('spec_date', models.DateField(blank=True, null=True)),
                ('body', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Body')),
            ],
            options={
                'db_table': 'ingest_previous_spectra',
                'verbose_name': 'External Spectroscopy',
                'verbose_name_plural': 'External Spectroscopy',
            },
        ),
    ]