# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_auto_20151022_2348'),
    ]

    operations = [
        migrations.CreateModel(
            name='SourceMeasurement',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('obs_ra', models.FloatField(verbose_name=b'Observed RA')),
                ('obs_dec', models.FloatField(verbose_name=b'Observed Dec')),
                ('obs_mag', models.FloatField(verbose_name=b'Observed Magnitude')),
                ('err_obs_ra', models.FloatField(null=True, verbose_name=b'Error on Observed RA', blank=True)),
                ('err_obs_dec', models.FloatField(null=True, verbose_name=b'Error on Observed Dec', blank=True)),
                ('err_obs_mag', models.FloatField(null=True, verbose_name=b'Error on Observed Magnitude', blank=True)),
            ],
            options={
                'db_table': 'source_measurement',
                'verbose_name': 'Source Measurement',
                'verbose_name_plural': 'Source Measurements',
            },
        ),
        migrations.AlterField(
            model_name='block',
            name='site',
            field=models.CharField(max_length=3, choices=[(b'ogg', b'Haleakala'), (b'coj', b'Siding Spring'), (b'lsc', b'Cerro Tololo'), (b'elp', b'McDonald'), (b'cpt', b'Sutherland'), (b'tfn', b'Tenerife'), (b'sbg', b'SBIG cameras'), (b'sin', b'Sinistro cameras')]),
        ),
        migrations.AlterField(
            model_name='body',
            name='source_type',
            field=models.CharField(blank=True, max_length=1, null=True, verbose_name=b'Type of object', choices=[(b'N', b'NEO'), (b'A', b'Asteroid'), (b'C', b'Comet'), (b'K', b'KBO'), (b'E', b'Centaur'), (b'T', b'Trojan'), (b'U', b'Candidate'), (b'X', b'Did not exist'), (b'W', b'Was not interesting'), (b'D', b'Discovery, non NEO'), (b'J', b'Artificial satellite')]),
        ),
        migrations.AddField(
            model_name='sourcemeasurement',
            name='body',
            field=models.ForeignKey(to='core.Body'),
        ),
        migrations.AddField(
            model_name='sourcemeasurement',
            name='frame',
            field=models.ForeignKey(to='core.Record'),
        ),
    ]
