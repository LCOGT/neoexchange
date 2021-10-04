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
from django.db.models import Q
from django.dispatch import receiver
from django.core.files.storage import default_storage

from core.models.body import Body
from core.models.blocks import Block, SuperBlock


class CoreQuerySet(models.QuerySet):
    def block(self):
        block = ContentType.objects.get(app_label='core', model='block')
        return self.filter(content_type=block)

    def body(self):
        body = ContentType.objects.get(app_label='core', model='body')
        return self.filter(content_type=body)

    def sblock(self):
        sblock = ContentType.objects.get(app_label='core', model='superblock')
        return self.filter(content_type=sblock)

    def fullbody(self, *args, **kwargs):
        body = ContentType.objects.get(app_label='core', model='body')
        bodyid = kwargs.get('bodyid')
        if not bodyid:
            return self.filter(content_type=body)
        else:
            block = ContentType.objects.get(app_label='core', model='block')
            sblock = ContentType.objects.get(app_label='core', model='superblock')
            blockslist = Block.objects.filter(body=bodyid).values_list('id', flat=True)
            sblockslist = SuperBlock.objects.filter(body=bodyid).values_list('id', flat=True)
            query1 = Q(content_type=block, object_id__in=blockslist)
            query2 = Q(content_type=body, object_id=bodyid)
            query3 = Q(content_type=sblock, object_id__in=sblockslist)
            return self.filter(query1 | query2 | query3)


class CoreManager(models.Manager):
    def get_queryset(self):
        return CoreQuerySet(self.model, using=self._db)

    def body(self):
        return self.get_queryset().body()

    def block(self):
        return self.get_queryset().block()

    def sblock(self):
        return self.get_queryset().sblock()

    def fullbody(self, *args, **kwargs):
        return self.get_queryset().fullbody(*args, **kwargs)


class DataProduct(models.Model):
    """
    DataProducts model to help find and access files generated by NEOx
    """
    JPEG = 0
    GUIDER_GIF = 1
    FITS_IMAGE = 2
    FITS_SPECTRA = 3
    ALCDEF_TXT = 4
    MP4 = 5
    CSV = 6
    PNG_ASTRO = 7
    PNG_PHOTO = 8
    PNG_LIGHTCURVE_PHASED = 9
    PNG_LIGHTCURVE_UNPHASED = 10
    PNG_LIGHTCURVE_COMBINED_PHASED = 11
    PNG_LIGHTCURVE_COMBINED_UNPHASED = 12
    PNG_PERIODOGRAM = 13
    PNG_DATAWINDOW = 14
    PNG_FWHM = 15
    PNG_ZP = 16
    PDS_XML = 20
    FRAME_GIF = 22
    DP_CHOICES = (
                    (JPEG, 'JPEG'),
                    (GUIDER_GIF, 'Spectroscopy Guider GIF'),
                    (FRAME_GIF, 'Thumbnail Frame GIF'),
                    (FITS_IMAGE, 'FITS Image'),
                    (FITS_SPECTRA, 'FITS Spectra'),
                    (ALCDEF_TXT, 'ALCDEF Lightcurve  file'),
                    (MP4, 'MP4'),
                    (CSV, 'CSV'),
                    (PNG_ASTRO, 'PNG astrometric ref stars'),
                    (PNG_PHOTO, 'PNG photometric ref stars'),
                    (PNG_LIGHTCURVE_PHASED, 'Block light curve PNG (phased)'),
                    (PNG_LIGHTCURVE_UNPHASED, 'Block light curve PNG (unphased)'),
                    (PNG_LIGHTCURVE_COMBINED_PHASED, 'Combined light curve PNG (phased)'),
                    (PNG_LIGHTCURVE_COMBINED_UNPHASED, 'Combined light curve PNG (unphased)'),
                    (PNG_PERIODOGRAM, 'Period finder periodogram PNG'),
                    (PNG_DATAWINDOW, 'Period finder data window PNG'),
                    (PNG_FWHM, 'FWHM condition PNG'),
                    (PNG_ZP, 'Zero point PNG'),
                    (PDS_XML, 'Planetary Data System (PDS) XML'),
                    (99, 'Other')
                )

    filetype = models.PositiveSmallIntegerField('Type of file to be stored.', choices=DP_CHOICES)
    product = models.FileField('Filefield for actual data product.', upload_to='products/', blank=True)
    created = models.DateTimeField('Datetime of the products creation or most recent update.', default=datetime.utcnow)
    update = models.BooleanField('Flag for allowing automated updates. Set to False for robust storage.', default=True)
    # GenericForeignKey stuff from ContentTypes
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    # Custom managers
    objects = models.Manager()
    content = CoreManager()

    def __str__(self):
        return f"{self.get_filetype_display()} for {self.content_type.name} - {self.object_id}"

    def save(self, *args, **kwargs):
        if not kwargs.get('new_file'):
            try:
                this = DataProduct.objects.get(id=self.id)
                this.product.delete(save=False)
            except DataProduct.DoesNotExist:
                pass

        super(DataProduct, self).save(*args, **kwargs)


@receiver(models.signals.post_delete, sender=DataProduct)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding `MediaFile` object is deleted.
    """
    if instance.product:
        if default_storage.exists(instance.product.path):
            default_storage.delete(instance.product.path)
