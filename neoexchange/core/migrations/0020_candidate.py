# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_auto_20160421_2144'),
    ]

    operations = [
        migrations.CreateModel(
            name='Candidate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('cand_id', models.PositiveIntegerField(verbose_name=b'Candidate Id')),
                ('score', models.FloatField(verbose_name=b'Candidate Score')),
                ('avg_midpoint', models.DateTimeField(verbose_name=b'Average UTC midpoint')),
                ('avg_x', models.FloatField(verbose_name=b'Average CCD X co-ordinate')),
                ('avg_y', models.FloatField(verbose_name=b'Average CCD Y co-ordinate')),
                ('avg_ra', models.FloatField(verbose_name=b'Average Observed RA (degrees)')),
                ('avg_dec', models.FloatField(verbose_name=b'Average Observed Dec (degrees)')),
                ('avg_mag', models.FloatField(null=True, verbose_name=b'Average Observed Magnitude', blank=True)),
                ('speed', models.FloatField(verbose_name=b'Speed (degrees/day)')),
                ('sky_motion_pa', models.FloatField(verbose_name=b'Position angle of motion on the sky (degrees)')),
                ('detections', models.BinaryField(verbose_name=b'Detections array', null=True, blank=True)),
                ('block', models.ForeignKey(to='core.Block', on_delete=models.deletion.CASCADE)),
            ],
            options={
                'verbose_name': 'Candidate',
            },
        ),
    ]
