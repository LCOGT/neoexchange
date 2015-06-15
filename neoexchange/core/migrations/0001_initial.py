# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Block',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('telclass', models.CharField(default=b'1m0', max_length=3, choices=[(b'1m0', b'1-meter'), (b'2m0', b'2-meter'), (b'0m4', b'0.4-meter')])),
                ('site', models.CharField(max_length=3, choices=[(b'ogg', b'Haleakala'), (b'coj', b'Siding Spring'), (b'lsc', b'Cerro Tololo'), (b'elp', b'McDonald'), (b'cpt', b'Sutherland')])),
                ('block_start', models.DateTimeField(null=True, blank=True)),
                ('block_end', models.DateTimeField(null=True, blank=True)),
                ('tracking_number', models.CharField(max_length=10, null=True, blank=True)),
                ('when_observed', models.DateTimeField(null=True, blank=True)),
                ('active', models.BooleanField(default=False)),
            ],
            options={
                'db_table': 'ingest_block',
                'verbose_name': 'Observation Block',
                'verbose_name_plural': 'Observation Blocks',
            },
        ),
        migrations.CreateModel(
            name='Body',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('provisional_name', models.CharField(max_length=15, null=True, verbose_name=b'Provisional MPC designation', blank=True)),
                ('provisional_packed', models.CharField(max_length=7, null=True, verbose_name=b'MPC name in packed format', blank=True)),
                ('name', models.CharField(max_length=15, null=True, verbose_name=b'Designation', blank=True)),
                ('origin', models.CharField(default=b'M', choices=[(b'M', b'Minor Planet Center'), (b'N', b'NASA ARM'), (b'S', b'Spaceguard'), (b'D', b'NEODSYS'), (b'G', b'Goldstone'), (b'A', b'Arecibo')], max_length=1, blank=True, null=True, verbose_name=b'Where did this target come from?')),
                ('source_type', models.CharField(blank=True, max_length=1, null=True, verbose_name=b'Type of object', choices=[(b'N', b'NEO'), (b'A', b'Asteroid'), (b'C', b'Comet'), (b'K', b'KBO'), (b'E', b'Centaur'), (b'T', b'Trojan'), (b'U', b'Unknown/NEO Candidate'), (b'X', b'Did not exist'), (b'W', b'Was not interesting')])),
                ('elements_type', models.CharField(blank=True, max_length=16, null=True, verbose_name=b'Elements type', choices=[(b'MPC_MINOR_PLANET', b'MPC Minor Planet'), (b'MPC_COMET', b'MPC Comet')])),
                ('active', models.BooleanField(default=False, verbose_name=b'Actively following?')),
                ('fast_moving', models.BooleanField(default=False, verbose_name=b'Is this object fast?')),
                ('urgency', models.IntegerField(help_text=b'how urgent is this?', null=True, blank=True)),
                ('epochofel', models.DateTimeField(null=True, verbose_name=b'Epoch of elements', blank=True)),
                ('orbinc', models.FloatField(null=True, verbose_name=b'Orbital inclination in deg', blank=True)),
                ('longascnode', models.FloatField(null=True, verbose_name=b'Longitude of Ascending Node (deg)', blank=True)),
                ('argofperih', models.FloatField(null=True, verbose_name=b'Arg of perihelion (deg)', blank=True)),
                ('eccentricity', models.FloatField(null=True, verbose_name=b'Eccentricity', blank=True)),
                ('meandist', models.FloatField(help_text=b'for asteroids', null=True, verbose_name=b'Mean distance (AU)', blank=True)),
                ('meananom', models.FloatField(help_text=b'for asteroids', null=True, verbose_name=b'Mean Anomaly (deg)', blank=True)),
                ('perihdist', models.FloatField(help_text=b'for comets', null=True, verbose_name=b'Perihelion distance (AU)', blank=True)),
                ('epochofperih', models.DateTimeField(help_text=b'for comets', null=True, verbose_name=b'Epoch of perihelion', blank=True)),
                ('abs_mag', models.FloatField(null=True, verbose_name=b'H - absolute magnitude', blank=True)),
                ('slope', models.FloatField(null=True, verbose_name=b'G - slope parameter', blank=True)),
                ('ingest', models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={
                'db_table': 'ingest_body',
                'verbose_name': 'Minor Body',
                'verbose_name_plural': 'Minor Bodies',
            },
        ),
        migrations.CreateModel(
            name='Proposal',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(max_length=20)),
                ('title', models.CharField(max_length=255)),
                ('pi', models.CharField(default=b'', max_length=50)),
                ('tag', models.CharField(default=b'LCO', max_length=10)),
            ],
            options={
                'db_table': 'ingest_proposal',
            },
        ),
        migrations.CreateModel(
            name='Record',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('site', models.CharField(max_length=3, verbose_name=b'3-letter site code')),
                ('instrument', models.CharField(max_length=4, verbose_name=b'instrument code')),
                ('filter', models.CharField(max_length=15, verbose_name=b'filter class')),
                ('filename', models.CharField(max_length=31)),
                ('exp', models.FloatField(verbose_name=b'exposure time in seconds')),
                ('whentaken', models.DateTimeField()),
                ('block', models.ForeignKey(to='core.Block')),
            ],
            options={
                'db_table': 'ingest_record',
                'verbose_name': 'Observation Record',
                'verbose_name_plural': 'Observation Records',
            },
        ),
        migrations.AddField(
            model_name='block',
            name='body',
            field=models.ForeignKey(to='core.Body'),
        ),
        migrations.AddField(
            model_name='block',
            name='proposal',
            field=models.ForeignKey(to='core.Proposal'),
        ),
    ]
