# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-06-13 01:21
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0046_auto_20190411_2227'),
    ]

    operations = [
        migrations.RenameField(
            model_name='block',
            old_name='tracking_number',
            new_name='request_number',
        ),
        migrations.RemoveField(
            model_name='block',
            name='groupid',
        ),
        migrations.RemoveField(
            model_name='block',
            name='proposal',
        ),
    ]
