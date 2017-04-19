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
