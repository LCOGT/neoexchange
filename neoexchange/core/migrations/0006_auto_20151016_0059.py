# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='body',
            name='num_obs',
            field=models.IntegerField(null=True, verbose_name=b'Number of observations', blank=True),
        ),
    ]
