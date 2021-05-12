"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2014-2019 LCO
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""
from datetime import datetime

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models

from core.models.body import Body
from core.models.blocks import Block

DP_CHOICES = (
                (0, 'JPEG'),
                (1, 'GIF'),
                (2, 'FITS Image'),
                (3, 'FITS Spectra'),
                (4, 'ALCDEF file'),
                (5, 'MP4'),
                (6, 'CSV'),
                (7, 'PNG'),
                (99, 'Other')
            )

class BlockManager(models.Manager):
    def get_queryset(self):
        block = ContentType.objects.get(app_label='core', model='block')
        return super().get_queryset().filter(content_type=block)

class BodyManager(models.Manager):
    def get_queryset(self):
        body = ContentType.objects.get(app_label='core', model='body')
        return super().get_queryset().filter(content_type=body)

class DataProduct(models.Model):
    filetype = models.PositiveSmallIntegerField(choices=DP_CHOICES)
    product = models.FileField(upload_to='products/')
    created = models.DateTimeField(default=datetime.utcnow)
    # GenericForeignKey stuff from ContentTypes
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    # Custom managers
    objects = models.Manager()
    body_objects = BodyManager()
    block_objects = BlockManager()

    def __str__(self):
        return f"{self.get_filetype_display()} for {self.content_type.name} - {self.object_id}"
