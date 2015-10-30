# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_auto_20151029_1846'),
    ]

    operations = [
        migrations.AlterField(
            model_name='frame',
            name='quality',
            field=models.IntegerField(default=-1, help_text=b'Frame Quality (-1: unassessed)', verbose_name=b'Frame Quality'),
        ),
    ]
