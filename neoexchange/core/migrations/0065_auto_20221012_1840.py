# Generated by Django 3.1.14 on 2022-10-12 18:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0064_auto_20220128_2217'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dataproduct',
            name='filetype',
            field=models.PositiveSmallIntegerField(choices=[(0, 'JPEG'), (1, 'Spectroscopy Guider GIF'), (22, 'Thumbnail Frame GIF'), (2, 'FITS Image'), (3, 'FITS Spectra'), (4, 'ALCDEF Lightcurve file'), (30, 'DART mission Lightcurve file'), (23, 'Periodogram output file'), (24, 'Model Lightcurve output file'), (25, 'Parameter file used to create DAMIT lightcurve models'), (26, 'Shape Model output file'), (5, 'MP4'), (6, 'CSV'), (7, 'PNG astrometric ref stars'), (8, 'PNG photometric ref stars'), (9, 'Block light curve PNG (phased)'), (10, 'Block light curve PNG (unphased)'), (11, 'Combined light curve PNG (phased)'), (12, 'Combined light curve PNG (unphased)'), (13, 'Period finder periodogram PNG'), (14, 'Period finder data window PNG'), (15, 'FWHM condition PNG'), (16, 'Zero point PNG'), (20, 'Planetary Data System (PDS) XML'), (99, 'Other')], verbose_name='Type of file to be stored.'),
        ),
    ]
