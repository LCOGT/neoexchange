# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-08-31 00:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0050_colorvalues_physicalparameters'),
    ]

    operations = [
        migrations.RenameField(
            model_name='designations',
            old_name='desig_notes',
            new_name='notes',
        ),
        migrations.RenameField(
            model_name='designations',
            old_name='desig',
            new_name='value',
        ),
        migrations.AlterField(
            model_name='physicalparameters',
            name='parameter_type',
            field=models.CharField(blank=True, choices=[('H', 'Absolute Magnitude'), ('G', 'Phase Slope'), ('D', 'Diameter'), ('R', 'Density'), ('P', 'Rotation Period'), ('A', 'LC Amplitude'), ('O', 'Pole Orientation'), ('ab', 'Albedo'), ('Y', 'Yarkovsky Drift'), ('E', 'Coma Extent'), ('M', 'Mass')], max_length=2, null=True, verbose_name='Physical Parameter Type'),
        ),
    ]
