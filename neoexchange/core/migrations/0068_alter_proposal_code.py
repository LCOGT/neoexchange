# Generated by Django 4.2.8 on 2023-12-19 21:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0067_merge_20230524_2317'),
    ]

    operations = [
        migrations.AlterField(
            model_name='proposal',
            name='code',
            field=models.CharField(max_length=55),
        ),
    ]
