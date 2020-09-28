# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_auto_20151022_2348'),
    ]

    operations = [
        migrations.CreateModel(
            name='Frame',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('sitecode', models.CharField(max_length=4, verbose_name=b'MPC site code')),
                ('instrument', models.CharField(max_length=4, verbose_name=b'instrument code', blank=True)),
                ('filter', models.CharField(max_length=15, verbose_name=b'filter class')),
                ('filename', models.CharField(max_length=40, verbose_name=b'FITS filename', blank=True)),
                ('exptime', models.FloatField(null=True, verbose_name=b'Exposure time in seconds', blank=True)),
                ('midpoint', models.DateTimeField(verbose_name=b'UTC date/time of frame midpoint')),
                ('quality', models.IntegerField(default=-1, verbose_name=b'Frame Quality (-1: unassessed)')),
                ('zeropoint', models.FloatField(null=True, verbose_name=b'Frame zeropoint (mag.)', blank=True)),
                ('zeropoint_err', models.FloatField(null=True, verbose_name=b'Error on Frame zeropoint (mag.)', blank=True)),
                ('fwhm', models.FloatField(null=True, verbose_name=b'Full width at half maximum (FWHM; arcsec)', blank=True)),
                ('frametype', models.SmallIntegerField(default=0, verbose_name=b'Frame Type', choices=[(0, b'Single frame'), (1, b'Stack of frames'), (2, b'Non-LCOGT data'), (3, b'Satellite data'), (4, b'Spectrum')])),
                ('extrainfo', models.TextField(blank=True)),
                ('rms_of_fit', models.FloatField(null=True, verbose_name=b'RMS of astrometric fit (arcsec)', blank=True)),
                ('nstars_in_fit', models.FloatField(null=True, verbose_name=b'No. of stars used in astrometric fit', blank=True)),
                ('time_uncertainty', models.FloatField(null=True, verbose_name=b'Time uncertainty (seconds)', blank=True)),
            ],
            options={
                'db_table': 'ingest_frame',
                'verbose_name': 'Observed Frame',
                'verbose_name_plural': 'Observed Frames',
            },
        ),
        migrations.RemoveField(
            model_name='record',
            name='block',
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
        migrations.DeleteModel(
            name='Record',
        ),
        migrations.AddField(
            model_name='frame',
            name='block',
            field=models.ForeignKey(blank=True, to='core.Block', null=True, on_delete=models.deletion.CASCADE),
        ),
    ]
