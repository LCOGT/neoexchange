# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_auto_20150716_0436'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='body',
            options={'ordering': ['-ingest', '-active'], 'verbose_name': 'Minor Body', 'verbose_name_plural': 'Minor Bodies'},
        ),
        migrations.AddField(
            model_name='body',
            name='arc_length',
            field=models.FloatField(null=True, verbose_name=b'Length of observed arc (days)', blank=True),
        ),
        migrations.AddField(
            model_name='body',
            name='discovery_date',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='body',
            name='not_seen',
            field=models.FloatField(null=True, verbose_name=b'Time since last observation (days)', blank=True),
        ),
        migrations.AddField(
            model_name='body',
            name='num_obs',
            field=models.IntegerField(help_text=b'Number of observations', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='body',
            name='score',
            field=models.IntegerField(help_text=b'NEOCP digest2 score', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='body',
            name='update_time',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='body',
            name='updated',
            field=models.BooleanField(default=False, verbose_name=b'Has this object been updated?'),
        ),
    ]
