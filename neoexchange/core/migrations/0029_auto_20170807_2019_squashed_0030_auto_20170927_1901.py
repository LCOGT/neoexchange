# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2017-09-27 19:02
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    replaces = [(b'core', '0029_auto_20170807_2019'), (b'core', '0030_auto_20170927_1901')]

    dependencies = [
        ('core', '0028_auto_20170713_1517'),
    ]

    operations = [
        migrations.CreateModel(
            name='SuperBlock',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cadence', models.BooleanField(default=False)),
                ('block_start', models.DateTimeField(blank=True, null=True)),
                ('block_end', models.DateTimeField(blank=True, null=True)),
                ('groupid', models.CharField(blank=True, max_length=55, null=True)),
                ('tracking_number', models.CharField(blank=True, max_length=10, null=True)),
                ('period', models.FloatField(blank=True, null=True, verbose_name=b'Spacing between cadence observations (hours)')),
                ('jitter', models.FloatField(blank=True, null=True, verbose_name=b'Acceptable deviation before or after strict period (hours)')),
                ('timeused', models.FloatField(blank=True, null=True, verbose_name=b'Time used (seconds)')),
                ('active', models.BooleanField(default=False)),
                ('body', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Body')),
                ('proposal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Proposal')),
                ('rapid_response', models.BooleanField(default=False, verbose_name=b'Is this a ToO/Rapid Response observation?')),
            ],
            options={
                'db_table': 'ingest_superblock',
                'verbose_name': 'SuperBlock',
                'verbose_name_plural': 'SuperBlocks',
            },
        ),
        migrations.AddField(
            model_name='block',
            name='superblock',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.SuperBlock'),
        ),
        migrations.AlterField(
            model_name='body',
            name='origin',
            field=models.CharField(blank=True, choices=[(b'M', b'Minor Planet Center'), (b'N', b'NASA ARM'), (b'S', b'Spaceguard'), (b'D', b'NEODSYS'), (b'G', b'Goldstone'), (b'A', b'Arecibo'), (b'R', b'Goldstone & Arecibo'), (b'L', b'LCOGT'), (b'Y', b'Yarkovsky')], default=b'M', max_length=1, null=True, verbose_name=b'Where did this target come from?'),
        ),
    ]
