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
            model_name='proposal',
            name='active',
            field=models.BooleanField(default=True, verbose_name=b'Proposal active?'),
        ),
    ]
