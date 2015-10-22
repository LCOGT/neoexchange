# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_auto_20151016_0059'),
    ]

    operations = [
        migrations.AlterField(
            model_name='block',
            name='num_observed',
            field=models.IntegerField(help_text=b'No. of scheduler blocks executed', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='block',
            name='when_observed',
            field=models.DateTimeField(help_text=b'Date/time of latest frame', null=True, blank=True),
        ),
    ]
