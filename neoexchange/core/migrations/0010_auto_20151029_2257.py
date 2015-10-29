# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_auto_20151029_1925'),
    ]

    operations = [
        migrations.AlterField(
            model_name='frame',
            name='quality',
            field=models.CharField(default=b' ', help_text=b'Comma separated list of frame/condition flags', max_length=40, verbose_name=b'Frame Quality flags', blank=True),
        ),
    ]
