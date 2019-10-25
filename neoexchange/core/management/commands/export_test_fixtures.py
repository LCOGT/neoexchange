"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2015-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from sys import argv
from datetime import datetime, timedelta
from io import StringIO

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.core import serializers

from core.models import SourceMeasurement, Frame, CatalogSources

class Command(BaseCommand):

    """
    Export content following relationships. We use XML format for some content types because it preserves the custom field info.
    """

    help = 'Export content following relationships'

    def handle(self, **options):
        # Export the smaller tables in full
        with StringIO() as buf:
            call_command('dumpdata', 'auth.user','core','-e', 'core.sourcemeasurement', '-e', 'core.frame', '-e','core.catalogsources', stdout=buf)
            buf.seek(0)
            with open('core/fixtures/partial.json', 'w') as f:
                f.write(buf.read())

        frame_content = {
            'sourcemeas' : SourceMeasurement,
            'catalogsources' : CatalogSources
        }

        frame_ids = []
        for name, fc in frame_content.items():
            qs = fc.objects.all().order_by('-id')[0:50]
            ids = list(qs.values_list('id',flat=True))
            # Find IDs of the frames referenced by these objects
            frame_ids += ids
            data = serializers.serialize('xml', qs)
            with open('core/fixtures/{}.xml'.format(name),'w') as f:
                f.write(data)

        lco_ids = Frame.objects.filter(frametype=91).values_list('id',flat=True).order_by('id')[0:20]
        spect_ids = Frame.objects.filter(frametype=4).values_list('id',flat=True).order_by('id')[0:20]
        frame_ids += list(lco_ids) + list(spect_ids)

        data = serializers.serialize('xml', Frame.objects.filter(id__in=frame_ids))
        with open('core/fixtures/frames.xml','w') as f:
            f.write(data)
