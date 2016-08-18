# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_catalogsources'),
    ]

    operations = [
        migrations.AddField(
            model_name='catalogsources',
            name='flux_max',
            field=models.FloatField(null=True, verbose_name=b'Peak flux above background', blank=True),
        ),
        migrations.AddField(
            model_name='catalogsources',
            name='threshold',
            field=models.FloatField(null=True, verbose_name=b'Detection threshold above background', blank=True),
        ),
    ]
