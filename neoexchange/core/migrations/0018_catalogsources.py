# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_auto_20160222_1513'),
    ]

    operations = [
        migrations.CreateModel(
            name='CatalogSources',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('obs_x', models.FloatField(verbose_name=b'CCD X co-ordinate')),
                ('obs_y', models.FloatField(verbose_name=b'CCD Y co-ordinate')),
                ('obs_ra', models.FloatField(verbose_name=b'Observed RA')),
                ('obs_dec', models.FloatField(verbose_name=b'Observed Dec')),
                ('obs_mag', models.FloatField(null=True, verbose_name=b'Observed Magnitude', blank=True)),
                ('err_obs_ra', models.FloatField(null=True, verbose_name=b'Error on Observed RA', blank=True)),
                ('err_obs_dec', models.FloatField(null=True, verbose_name=b'Error on Observed Dec', blank=True)),
                ('err_obs_mag', models.FloatField(null=True, verbose_name=b'Error on Observed Magnitude', blank=True)),
                ('background', models.FloatField(verbose_name=b'Background')),
                ('major_axis', models.FloatField(verbose_name=b'Ellipse major axis')),
                ('minor_axis', models.FloatField(verbose_name=b'Ellipse minor axis')),
                ('position_angle', models.FloatField(verbose_name=b'Ellipse position angle')),
                ('ellipticity', models.FloatField(verbose_name=b'Ellipticity')),
                ('aperture_size', models.FloatField(null=True, verbose_name=b'Size of aperture (arcsec)', blank=True)),
                ('flags', models.IntegerField(default=0, help_text=b'Bitmask of flags', verbose_name=b'Source flags')),
                ('frame', models.ForeignKey(to='core.Frame')),
            ],
            options={
                'db_table': 'catalog_source',
                'verbose_name': 'Catalog Source',
                'verbose_name_plural': 'Catalog Sources',
            },
        ),
    ]
