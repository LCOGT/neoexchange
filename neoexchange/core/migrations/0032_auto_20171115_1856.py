# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2017-11-15 18:56
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0031_auto_20171114_2254'),
    ]

    operations = [
        migrations.AlterField(
            model_name='spectralinfo',
            name='tax_reference',
            field=models.CharField(blank=True, choices=[(b'PDS6', b'Neese, Asteroid Taxonomy V6.0. (2010).'), (b'BZ04', b'Binzel, et al. (2004).')], max_length=6, null=True, verbose_name=b'Reference source for Taxonomic data'),
        ),
    ]
