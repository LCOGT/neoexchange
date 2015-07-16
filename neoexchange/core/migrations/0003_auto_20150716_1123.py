# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_auto_20150714_0506'),
    ]

    operations = [
        migrations.AddField(
            model_name='block',
            name='num_observed',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='block',
            name='reported',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='block',
            name='when_reported',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
