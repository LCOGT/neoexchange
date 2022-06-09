# Generated by Django 3.1.13 on 2022-01-26 00:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0062_auto_20220102_1930'),
    ]

    operations = [
        migrations.AddField(
            model_name='block',
            name='tracking_rate',
            field=models.SmallIntegerField(choices=[(100, 'Target Tracking'), (50, 'Half-Rate Tracking'), (0, 'Sidereal Tracking'), (-99, 'Non-Standard Tracking')], default=100, verbose_name='Tracking Strategy'),
        ),
    ]