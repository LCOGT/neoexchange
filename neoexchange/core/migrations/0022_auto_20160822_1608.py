# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import core.models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_auto_20160804_2349'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='frame',
            name='x_size',
        ),
        migrations.RemoveField(
            model_name='frame',
            name='y_size',
        ),
        migrations.AddField(
            model_name='frame',
            name='wcs',
            field=core.models.WCSField(verbose_name=b'WCS info', null=True, blank=True),
        ),
    ]
