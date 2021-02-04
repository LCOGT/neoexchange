# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0016_auto_20151119_2021'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProposalPermission',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('proposal', models.ForeignKey(to='core.Proposal', on_delete=models.deletion.CASCADE)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.deletion.CASCADE)),
            ],
            options={
                'verbose_name': 'Proposal Permission',
            },
        ),
        migrations.AlterField(
            model_name='body',
            name='origin',
            field=models.CharField(default=b'M', choices=[(b'M', b'Minor Planet Center'), (b'N', b'NASA ARM'), (b'S', b'Spaceguard'), (b'D', b'NEODSYS'), (b'G', b'Goldstone'), (b'A', b'Arecibo'), (b'R', b'Goldstone & Arecibo'), (b'L', b'LCOGT')], max_length=1, blank=True, null=True, verbose_name=b'Where did this target come from?'),
        ),
    ]
