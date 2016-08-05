# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_candidate'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='candidate',
            options={'verbose_name': 'Candidate'},
        ),
        migrations.AddField(
            model_name='frame',
            name='frameid',
            field=models.IntegerField(null=True, verbose_name=b'Archive ID', blank=True),
        ),
        migrations.AddField(
            model_name='frame',
            name='x_size',
            field=models.IntegerField(null=True, verbose_name=b'Size x pixels', blank=True),
        ),
        migrations.AddField(
            model_name='frame',
            name='y_size',
            field=models.IntegerField(null=True, verbose_name=b'Size y pixels', blank=True),
        ),
    ]
