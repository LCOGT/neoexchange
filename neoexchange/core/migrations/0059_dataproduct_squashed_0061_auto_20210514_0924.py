# Generated by Django 3.1.10 on 2021-06-21 23:40

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    replaces = [('core', '0059_dataproduct'), ('core', '0060_auto_20210512_1359'), ('core', '0061_auto_20210514_0924')]

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('core', '0058_auto_20201119_1751'),
    ]

    operations = [
        migrations.CreateModel(
            name='DataProduct',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filetype', models.PositiveSmallIntegerField(choices=[(0, 'JPEG'), (1, 'Guider GIF'), (2, 'FITS Image'), (3, 'FITS Spectra'), (4, 'ALCDEF file'), (5, 'MP4'), (6, 'CSV'), (7, 'PNG astrometric ref stars'), (8, 'PNG photometric ref stars'), (9, 'Block light curve PNG (phased)'), (10, 'Block light curve PNG (unphased)'), (11, 'Combined light curve PNG (phased)'), (12, 'Combined light curve PNG (unphased)'), (13, 'Period finder periodogram PNG'), (14, 'Period finder data window PNG'), (15, 'FWHM condition PNG'), (16, 'Zero point PNG'), (20, 'Planetary Data System (PDS) XML'), (99, 'Other')])),
                ('product', models.FileField(blank=True, upload_to='products/')),
                ('created', models.DateTimeField(default=datetime.datetime.utcnow)),
                ('object_id', models.PositiveIntegerField()),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
            ],
        ),
    ]