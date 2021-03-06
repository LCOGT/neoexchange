# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-05-30 17:17
from __future__ import unicode_literals

import core.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0035_merge_20180511_0020'),
    ]

    operations = [
        migrations.AlterField(
            model_name='block',
            name='exp_length',
            field=models.FloatField(blank=True, null=True, verbose_name='Exposure length in seconds'),
        ),
        migrations.AlterField(
            model_name='block',
            name='num_observed',
            field=models.IntegerField(blank=True, help_text='No. of scheduler blocks executed', null=True),
        ),
        migrations.AlterField(
            model_name='block',
            name='site',
            field=models.CharField(choices=[('ogg', 'Haleakala'), ('coj', 'Siding Spring'), ('lsc', 'Cerro Tololo'), ('elp', 'McDonald'), ('cpt', 'Sutherland'), ('tfn', 'Tenerife'), ('sbg', 'SBIG cameras'), ('sin', 'Sinistro cameras')], max_length=3),
        ),
        migrations.AlterField(
            model_name='block',
            name='telclass',
            field=models.CharField(choices=[('1m0', '1-meter'), ('2m0', '2-meter'), ('0m4', '0.4-meter')], default='1m0', max_length=3),
        ),
        migrations.AlterField(
            model_name='block',
            name='when_observed',
            field=models.DateTimeField(blank=True, help_text='Date/time of latest frame', null=True),
        ),
        migrations.AlterField(
            model_name='body',
            name='abs_mag',
            field=models.FloatField(blank=True, null=True, verbose_name='H - absolute magnitude'),
        ),
        migrations.AlterField(
            model_name='body',
            name='active',
            field=models.BooleanField(default=False, verbose_name='Actively following?'),
        ),
        migrations.AlterField(
            model_name='body',
            name='arc_length',
            field=models.FloatField(blank=True, null=True, verbose_name='Length of observed arc (days)'),
        ),
        migrations.AlterField(
            model_name='body',
            name='argofperih',
            field=models.FloatField(blank=True, null=True, verbose_name='Arg of perihelion (deg)'),
        ),
        migrations.AlterField(
            model_name='body',
            name='eccentricity',
            field=models.FloatField(blank=True, null=True, verbose_name='Eccentricity'),
        ),
        migrations.AlterField(
            model_name='body',
            name='elements_type',
            field=models.CharField(blank=True, choices=[('MPC_MINOR_PLANET', 'MPC Minor Planet'), ('MPC_COMET', 'MPC Comet')], max_length=16, null=True, verbose_name='Elements type'),
        ),
        migrations.AlterField(
            model_name='body',
            name='epochofel',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Epoch of elements'),
        ),
        migrations.AlterField(
            model_name='body',
            name='epochofperih',
            field=models.DateTimeField(blank=True, help_text='for comets', null=True, verbose_name='Epoch of perihelion'),
        ),
        migrations.AlterField(
            model_name='body',
            name='fast_moving',
            field=models.BooleanField(default=False, verbose_name='Is this object fast?'),
        ),
        migrations.AlterField(
            model_name='body',
            name='longascnode',
            field=models.FloatField(blank=True, null=True, verbose_name='Longitude of Ascending Node (deg)'),
        ),
        migrations.AlterField(
            model_name='body',
            name='meananom',
            field=models.FloatField(blank=True, help_text='for asteroids', null=True, verbose_name='Mean Anomaly (deg)'),
        ),
        migrations.AlterField(
            model_name='body',
            name='meandist',
            field=models.FloatField(blank=True, help_text='for asteroids', null=True, verbose_name='Mean distance (AU)'),
        ),
        migrations.AlterField(
            model_name='body',
            name='name',
            field=models.CharField(blank=True, max_length=15, null=True, verbose_name='Designation'),
        ),
        migrations.AlterField(
            model_name='body',
            name='not_seen',
            field=models.FloatField(blank=True, null=True, verbose_name='Time since last observation (days)'),
        ),
        migrations.AlterField(
            model_name='body',
            name='num_obs',
            field=models.IntegerField(blank=True, null=True, verbose_name='Number of observations'),
        ),
        migrations.AlterField(
            model_name='body',
            name='orbinc',
            field=models.FloatField(blank=True, null=True, verbose_name='Orbital inclination in deg'),
        ),
        migrations.AlterField(
            model_name='body',
            name='origin',
            field=models.CharField(blank=True, choices=[('M', 'Minor Planet Center'), ('N', 'NASA'), ('S', 'Spaceguard'), ('D', 'NEODSYS'), ('G', 'Goldstone'), ('A', 'Arecibo'), ('R', 'Goldstone & Arecibo'), ('L', 'LCOGT'), ('Y', 'Yarkovsky'), ('T', 'Trojan')], default='M', max_length=1, null=True, verbose_name='Where did this target come from?'),
        ),
        migrations.AlterField(
            model_name='body',
            name='perihdist',
            field=models.FloatField(blank=True, help_text='for comets', null=True, verbose_name='Perihelion distance (AU)'),
        ),
        migrations.AlterField(
            model_name='body',
            name='provisional_name',
            field=models.CharField(blank=True, max_length=15, null=True, verbose_name='Provisional MPC designation'),
        ),
        migrations.AlterField(
            model_name='body',
            name='provisional_packed',
            field=models.CharField(blank=True, max_length=7, null=True, verbose_name='MPC name in packed format'),
        ),
        migrations.AlterField(
            model_name='body',
            name='score',
            field=models.IntegerField(blank=True, help_text='NEOCP digest2 score', null=True),
        ),
        migrations.AlterField(
            model_name='body',
            name='slope',
            field=models.FloatField(blank=True, null=True, verbose_name='G - slope parameter'),
        ),
        migrations.AlterField(
            model_name='body',
            name='source_type',
            field=models.CharField(blank=True, choices=[('N', 'NEO'), ('A', 'Asteroid'), ('C', 'Comet'), ('K', 'KBO'), ('E', 'Centaur'), ('T', 'Trojan'), ('U', 'Candidate'), ('X', 'Did not exist'), ('W', 'Was not interesting'), ('D', 'Discovery, non NEO'), ('J', 'Artificial satellite'), ('H', 'Hyperbolic asteroids')], max_length=1, null=True, verbose_name='Type of object'),
        ),
        migrations.AlterField(
            model_name='body',
            name='updated',
            field=models.BooleanField(default=False, verbose_name='Has this object been updated?'),
        ),
        migrations.AlterField(
            model_name='body',
            name='urgency',
            field=models.IntegerField(blank=True, help_text='how urgent is this?', null=True),
        ),
        migrations.AlterField(
            model_name='candidate',
            name='avg_dec',
            field=models.FloatField(verbose_name='Average Observed Dec (degrees)'),
        ),
        migrations.AlterField(
            model_name='candidate',
            name='avg_mag',
            field=models.FloatField(blank=True, null=True, verbose_name='Average Observed Magnitude'),
        ),
        migrations.AlterField(
            model_name='candidate',
            name='avg_midpoint',
            field=models.DateTimeField(verbose_name='Average UTC midpoint'),
        ),
        migrations.AlterField(
            model_name='candidate',
            name='avg_ra',
            field=models.FloatField(verbose_name='Average Observed RA (degrees)'),
        ),
        migrations.AlterField(
            model_name='candidate',
            name='avg_x',
            field=models.FloatField(verbose_name='Average CCD X co-ordinate'),
        ),
        migrations.AlterField(
            model_name='candidate',
            name='avg_y',
            field=models.FloatField(verbose_name='Average CCD Y co-ordinate'),
        ),
        migrations.AlterField(
            model_name='candidate',
            name='cand_id',
            field=models.PositiveIntegerField(verbose_name='Candidate Id'),
        ),
        migrations.AlterField(
            model_name='candidate',
            name='detections',
            field=models.BinaryField(blank=True, null=True, verbose_name='Detections array'),
        ),
        migrations.AlterField(
            model_name='candidate',
            name='score',
            field=models.FloatField(verbose_name='Candidate Score'),
        ),
        migrations.AlterField(
            model_name='candidate',
            name='sky_motion_pa',
            field=models.FloatField(verbose_name='Position angle of motion on the sky (degrees)'),
        ),
        migrations.AlterField(
            model_name='candidate',
            name='speed',
            field=models.FloatField(verbose_name='Speed (degrees/day)'),
        ),
        migrations.AlterField(
            model_name='catalogsources',
            name='aperture_size',
            field=models.FloatField(blank=True, null=True, verbose_name='Size of aperture (arcsec)'),
        ),
        migrations.AlterField(
            model_name='catalogsources',
            name='background',
            field=models.FloatField(verbose_name='Background'),
        ),
        migrations.AlterField(
            model_name='catalogsources',
            name='ellipticity',
            field=models.FloatField(verbose_name='Ellipticity'),
        ),
        migrations.AlterField(
            model_name='catalogsources',
            name='err_obs_dec',
            field=models.FloatField(blank=True, null=True, verbose_name='Error on Observed Dec'),
        ),
        migrations.AlterField(
            model_name='catalogsources',
            name='err_obs_mag',
            field=models.FloatField(blank=True, null=True, verbose_name='Error on Observed Magnitude'),
        ),
        migrations.AlterField(
            model_name='catalogsources',
            name='err_obs_ra',
            field=models.FloatField(blank=True, null=True, verbose_name='Error on Observed RA'),
        ),
        migrations.AlterField(
            model_name='catalogsources',
            name='flags',
            field=models.IntegerField(default=0, help_text='Bitmask of flags', verbose_name='Source flags'),
        ),
        migrations.AlterField(
            model_name='catalogsources',
            name='flux_max',
            field=models.FloatField(blank=True, null=True, verbose_name='Peak flux above background'),
        ),
        migrations.AlterField(
            model_name='catalogsources',
            name='major_axis',
            field=models.FloatField(verbose_name='Ellipse major axis'),
        ),
        migrations.AlterField(
            model_name='catalogsources',
            name='minor_axis',
            field=models.FloatField(verbose_name='Ellipse minor axis'),
        ),
        migrations.AlterField(
            model_name='catalogsources',
            name='obs_dec',
            field=models.FloatField(verbose_name='Observed Dec'),
        ),
        migrations.AlterField(
            model_name='catalogsources',
            name='obs_mag',
            field=models.FloatField(blank=True, null=True, verbose_name='Observed Magnitude'),
        ),
        migrations.AlterField(
            model_name='catalogsources',
            name='obs_ra',
            field=models.FloatField(verbose_name='Observed RA'),
        ),
        migrations.AlterField(
            model_name='catalogsources',
            name='obs_x',
            field=models.FloatField(verbose_name='CCD X co-ordinate'),
        ),
        migrations.AlterField(
            model_name='catalogsources',
            name='obs_y',
            field=models.FloatField(verbose_name='CCD Y co-ordinate'),
        ),
        migrations.AlterField(
            model_name='catalogsources',
            name='position_angle',
            field=models.FloatField(verbose_name='Ellipse position angle'),
        ),
        migrations.AlterField(
            model_name='catalogsources',
            name='threshold',
            field=models.FloatField(blank=True, null=True, verbose_name='Detection threshold above background'),
        ),
        migrations.AlterField(
            model_name='frame',
            name='astrometric_catalog',
            field=models.CharField(default=' ', max_length=40, verbose_name='Astrometric catalog used'),
        ),
        migrations.AlterField(
            model_name='frame',
            name='exptime',
            field=models.FloatField(blank=True, null=True, verbose_name='Exposure time in seconds'),
        ),
        migrations.AlterField(
            model_name='frame',
            name='filename',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='FITS filename'),
        ),
        migrations.AlterField(
            model_name='frame',
            name='filter',
            field=models.CharField(default='B', max_length=15, verbose_name='filter class'),
        ),
        migrations.AlterField(
            model_name='frame',
            name='frameid',
            field=models.IntegerField(blank=True, null=True, verbose_name='Archive ID'),
        ),
        migrations.AlterField(
            model_name='frame',
            name='frametype',
            field=models.SmallIntegerField(choices=[(0, 'Single frame'), (1, 'Stack of frames'), (2, 'Non-LCOGT data'), (3, 'Satellite data'), (4, 'Spectrum'), (5, 'FITS LDAC catalog'), (6, 'BANZAI LDAC catalog'), (10, 'ORACDR QL frame'), (11, 'BANZAI QL frame'), (90, 'ORACDR reduced frame'), (91, 'BANZAI reduced frame')], default=0, verbose_name='Frame Type'),
        ),
        migrations.AlterField(
            model_name='frame',
            name='fwhm',
            field=models.FloatField(blank=True, null=True, verbose_name='Full width at half maximum (FWHM; arcsec)'),
        ),
        migrations.AlterField(
            model_name='frame',
            name='instrument',
            field=models.CharField(blank=True, max_length=4, null=True, verbose_name='instrument code'),
        ),
        migrations.AlterField(
            model_name='frame',
            name='midpoint',
            field=models.DateTimeField(verbose_name='UTC date/time of frame midpoint'),
        ),
        migrations.AlterField(
            model_name='frame',
            name='nstars_in_fit',
            field=models.FloatField(blank=True, null=True, verbose_name='No. of stars used in astrometric fit'),
        ),
        migrations.AlterField(
            model_name='frame',
            name='photometric_catalog',
            field=models.CharField(default=' ', max_length=40, verbose_name='Photometric catalog used'),
        ),
        migrations.AlterField(
            model_name='frame',
            name='quality',
            field=models.CharField(blank=True, default=' ', help_text='Comma separated list of frame/condition flags', max_length=40, verbose_name='Frame Quality flags'),
        ),
        migrations.AlterField(
            model_name='frame',
            name='rms_of_fit',
            field=models.FloatField(blank=True, null=True, verbose_name='RMS of astrometric fit (arcsec)'),
        ),
        migrations.AlterField(
            model_name='frame',
            name='sitecode',
            field=models.CharField(max_length=4, verbose_name='MPC site code'),
        ),
        migrations.AlterField(
            model_name='frame',
            name='time_uncertainty',
            field=models.FloatField(blank=True, null=True, verbose_name='Time uncertainty (seconds)'),
        ),
        migrations.AlterField(
            model_name='frame',
            name='wcs',
            field=core.models.WCSField(blank=True, null=True, verbose_name='WCS info'),
        ),
        migrations.AlterField(
            model_name='frame',
            name='zeropoint',
            field=models.FloatField(blank=True, null=True, verbose_name='Frame zeropoint (mag.)'),
        ),
        migrations.AlterField(
            model_name='frame',
            name='zeropoint_err',
            field=models.FloatField(blank=True, null=True, verbose_name='Error on Frame zeropoint (mag.)'),
        ),
        migrations.AlterField(
            model_name='panoptesreport',
            name='classifiers',
            field=models.TextField(blank=True, help_text='Volunteers usernames who found NEOs', null=True),
        ),
        migrations.AlterField(
            model_name='panoptesreport',
            name='subject_id',
            field=models.IntegerField(blank=True, null=True, verbose_name='Subject ID'),
        ),
        migrations.AlterField(
            model_name='panoptesreport',
            name='when_submitted',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Date sent to Zooniverse'),
        ),
        migrations.AlterField(
            model_name='previousspectra',
            name='spec_ir',
            field=models.URLField(blank=True, null=True, verbose_name='IR Spectra Link'),
        ),
        migrations.AlterField(
            model_name='previousspectra',
            name='spec_ref',
            field=models.CharField(blank=True, max_length=10, null=True, verbose_name='Spectra Reference'),
        ),
        migrations.AlterField(
            model_name='previousspectra',
            name='spec_source',
            field=models.CharField(blank=True, choices=[('S', 'SMASS'), ('M', 'MANOS'), ('U', 'Unknown'), ('O', 'Other')], max_length=1, null=True, verbose_name='Source'),
        ),
        migrations.AlterField(
            model_name='previousspectra',
            name='spec_vis',
            field=models.URLField(blank=True, null=True, verbose_name='Visible Spectra Link'),
        ),
        migrations.AlterField(
            model_name='previousspectra',
            name='spec_wav',
            field=models.CharField(blank=True, choices=[('Vis', 'Visible'), ('NIR', 'Near Infrared'), ('Vis+NIR', 'Both Visible and Near IR'), ('NA', 'None Yet.')], max_length=7, null=True, verbose_name='Wavelength'),
        ),
        migrations.AlterField(
            model_name='proposal',
            name='active',
            field=models.BooleanField(default=True, verbose_name='Proposal active?'),
        ),
        migrations.AlterField(
            model_name='proposal',
            name='pi',
            field=models.CharField(default='', help_text='Principal Investigator (PI)', max_length=50, verbose_name='PI'),
        ),
        migrations.AlterField(
            model_name='proposal',
            name='tag',
            field=models.CharField(default='LCOGT', max_length=10),
        ),
        migrations.AlterField(
            model_name='sourcemeasurement',
            name='aperture_size',
            field=models.FloatField(blank=True, null=True, verbose_name='Size of aperture (arcsec)'),
        ),
        migrations.AlterField(
            model_name='sourcemeasurement',
            name='astrometric_catalog',
            field=models.CharField(default=' ', max_length=40, verbose_name='Astrometric catalog used'),
        ),
        migrations.AlterField(
            model_name='sourcemeasurement',
            name='err_obs_dec',
            field=models.FloatField(blank=True, null=True, verbose_name='Error on Observed Dec'),
        ),
        migrations.AlterField(
            model_name='sourcemeasurement',
            name='err_obs_mag',
            field=models.FloatField(blank=True, null=True, verbose_name='Error on Observed Magnitude'),
        ),
        migrations.AlterField(
            model_name='sourcemeasurement',
            name='err_obs_ra',
            field=models.FloatField(blank=True, null=True, verbose_name='Error on Observed RA'),
        ),
        migrations.AlterField(
            model_name='sourcemeasurement',
            name='flags',
            field=models.CharField(blank=True, default=' ', help_text='Comma separated list of frame/condition flags', max_length=40, verbose_name='Frame Quality flags'),
        ),
        migrations.AlterField(
            model_name='sourcemeasurement',
            name='obs_dec',
            field=models.FloatField(blank=True, null=True, verbose_name='Observed Dec'),
        ),
        migrations.AlterField(
            model_name='sourcemeasurement',
            name='obs_mag',
            field=models.FloatField(blank=True, null=True, verbose_name='Observed Magnitude'),
        ),
        migrations.AlterField(
            model_name='sourcemeasurement',
            name='obs_ra',
            field=models.FloatField(blank=True, null=True, verbose_name='Observed RA'),
        ),
        migrations.AlterField(
            model_name='sourcemeasurement',
            name='photometric_catalog',
            field=models.CharField(default=' ', max_length=40, verbose_name='Photometric catalog used'),
        ),
        migrations.AlterField(
            model_name='sourcemeasurement',
            name='snr',
            field=models.FloatField(blank=True, null=True, verbose_name='Size of aperture (arcsec)'),
        ),
        migrations.AlterField(
            model_name='spectralinfo',
            name='tax_notes',
            field=models.CharField(blank=True, max_length=30, null=True, verbose_name='Notes on Taxonomic Classification'),
        ),
        migrations.AlterField(
            model_name='spectralinfo',
            name='tax_reference',
            field=models.CharField(blank=True, choices=[('PDS6', 'Neese, Asteroid Taxonomy V6.0. (2010).'), ('BZ04', 'Binzel, et al. (2004).')], max_length=6, null=True, verbose_name='Reference source for Taxonomic data'),
        ),
        migrations.AlterField(
            model_name='spectralinfo',
            name='tax_scheme',
            field=models.CharField(blank=True, choices=[('T', 'Tholen'), ('Ba', 'Barucci'), ('Td', 'Tedesco'), ('H', 'Howell'), ('S', 'SMASS'), ('B', 'Bus'), ('3T', 'S3OS2_TH'), ('3B', 'S3OS2_BB'), ('BD', 'Bus-DeMeo')], max_length=2, null=True, verbose_name='Taxonomic Scheme'),
        ),
        migrations.AlterField(
            model_name='spectralinfo',
            name='taxonomic_class',
            field=models.CharField(blank=True, max_length=6, null=True, verbose_name='Taxonomic Class'),
        ),
        migrations.AlterField(
            model_name='superblock',
            name='jitter',
            field=models.FloatField(blank=True, null=True, verbose_name='Acceptable deviation before or after strict period (hours)'),
        ),
        migrations.AlterField(
            model_name='superblock',
            name='period',
            field=models.FloatField(blank=True, null=True, verbose_name='Spacing between cadence observations (hours)'),
        ),
        migrations.AlterField(
            model_name='superblock',
            name='rapid_response',
            field=models.BooleanField(default=False, verbose_name='Is this a ToO/Rapid Response observation?'),
        ),
        migrations.AlterField(
            model_name='superblock',
            name='timeused',
            field=models.FloatField(blank=True, null=True, verbose_name='Time used (seconds)'),
        ),
    ]
