# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='block',
            name='exp_length',
            field=models.FloatField(null=True, verbose_name=b'Exposure length in seconds', blank=True),
        ),
        migrations.AddField(
            model_name='block',
            name='num_exposures',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='block',
            name='site',
            field=models.CharField(max_length=3, choices=[(b'ogg', b'Haleakala'), (b'coj', b'Siding Spring'), (b'lsc', b'Cerro Tololo'), (b'elp', b'McDonald'), (b'cpt', b'Sutherland'), (b'tfn', b'Tenerife')]),
        ),
        migrations.AlterField(
            model_name='body',
            name='origin',
            field=models.CharField(default=b'M', choices=[(b'M', b'Minor Planet Center'), (b'N', b'NASA ARM'), (b'S', b'Spaceguard'), (b'D', b'NEODSYS'), (b'G', b'Goldstone'), (b'A', b'Arecibo'), (b'L', b'LCOGT')], max_length=1, blank=True, null=True, verbose_name=b'Where did this target come from?'),
        ),
        migrations.AlterField(
            model_name='body',
            name='source_type',
            field=models.CharField(blank=True, max_length=1, null=True, verbose_name=b'Type of object', choices=[(b'N', b'NEO'), (b'A', b'Asteroid'), (b'C', b'Comet'), (b'K', b'KBO'), (b'E', b'Centaur'), (b'T', b'Trojan'), (b'U', b'Unknown/NEO Candidate'), (b'X', b'Did not exist'), (b'W', b'Was not interesting'), (b'D', b'Discovery, non NEO')]),
        ),
        migrations.AlterField(
            model_name='proposal',
            name='pi',
            field=models.CharField(default=b'', help_text=b'Principal Investigator (PI)', max_length=50, verbose_name=b'PI'),
        ),
        migrations.AlterField(
            model_name='proposal',
            name='tag',
            field=models.CharField(default=b'LCOGT', max_length=10),
        ),
    ]
