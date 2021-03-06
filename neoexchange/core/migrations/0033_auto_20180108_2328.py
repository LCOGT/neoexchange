# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-01-08 23:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0032_auto_20171115_1856'),
    ]

    operations = [
        migrations.AlterField(
            model_name='body',
            name='origin',
            field=models.CharField(blank=True, choices=[(b'M', b'Minor Planet Center'), (b'N', b'NASA'), (b'S', b'Spaceguard'), (b'D', b'NEODSYS'), (b'G', b'Goldstone'), (b'A', b'Arecibo'), (b'R', b'Goldstone & Arecibo'), (b'L', b'LCOGT'), (b'Y', b'Yarkovsky'), (b'T', b'Trojan')], default=b'M', max_length=1, null=True, verbose_name=b'Where did this target come from?'),
        ),
    ]
