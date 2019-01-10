"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2016-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from core.models import Frame, SourceMeasurement

from django.core.management.base import BaseCommand, CommandError
from datetime import datetime

class Command(BaseCommand):
    help = 'Update Frames with catalogue in from SourceMeasurements'

    def handle(self, *args, **options):
        self.stdout.write("==== Updating Frames from SourceMeasurements %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        sources = SourceMeasurement.objects.all()
        for source in sources:
            frame = source.frame
            frame.astrometric_catalog = source.astrometric_catalog
            frame.photometric_catalog = source.photometric_catalog
            frame.save()
        self.stdout.write("Updated {} SourceMeasurements".format(sources.count()))
