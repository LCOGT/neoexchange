# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-11-12 22:43
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    replaces = [('core', '0052_auto_20191112_2225'), ('core', '0053_auto_20191112_2226'), ('core', '0054_auto_20191112_2229')]

    dependencies = [
        ('core', '0051_auto_20190831_0028'),
    ]

    operations = [
        migrations.AlterField(
            model_name='physicalparameters',
            name='notes',
            field=models.TextField(blank=True, null=True, verbose_name='Notes on this value'),
        ),
        migrations.AlterField(
            model_name='physicalparameters',
            name='reference',
            field=models.TextField(blank=True, max_length=50, null=True, verbose_name='Reference for this value'),
        ),
        migrations.AlterField(
            model_name='colorvalues',
            name='notes',
            field=models.TextField(blank=True, max_length=50, null=True, verbose_name='Notes on this value'),
        ),
        migrations.AlterField(
            model_name='colorvalues',
            name='reference',
            field=models.TextField(blank=True, max_length=50, null=True, verbose_name='Reference for this value'),
        ),
    ]
