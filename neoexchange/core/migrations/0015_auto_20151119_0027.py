# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_auto_20151119_0025'),
    ]

    operations = [
        migrations.AlterField(
            model_name='frame',
            name='sitecode',
            field=models.CharField(default=b'none', max_length=4, verbose_name=b'MPC site code'),
        ),
    ]
