# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_auto_20151103_2036'),
    ]

    operations = [
        migrations.AlterField(
            model_name='frame',
            name='extrainfo',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='frame',
            name='filename',
            field=models.CharField(max_length=40, null=True, verbose_name=b'FITS filename', blank=True),
        ),
        migrations.AlterField(
            model_name='frame',
            name='instrument',
            field=models.CharField(max_length=4, null=True, verbose_name=b'instrument code', blank=True),
        ),
    ]
