# Generated by Django 3.1.2 on 2021-05-12 11:15

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('core', '0058_auto_20201119_1751'),
    ]

    operations = [
        migrations.CreateModel(
            name='DataProduct',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filetype', models.PositiveSmallIntegerField(choices=[(0, 'JPEG'), (1, 'GIF'), (2, 'FITS Image'), (3, 'FITS Spectra'), (4, 'ALCDEF file'), (5, 'MP4'), (6, 'CSV'), (7, 'PNG'), (99, 'Other')])),
                ('product', models.FileField(upload_to='products/')),
                ('created', models.DateTimeField(default=datetime.datetime.utcnow)),
                ('object_id', models.PositiveIntegerField()),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
            ],
        ),
    ]
