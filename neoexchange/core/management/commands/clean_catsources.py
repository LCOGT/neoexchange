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

from django.core.management.base import BaseCommand, CommandError

from core.models import Block, CatalogSources, Frame

class Command(BaseCommand):

    help = 'Fear The Vacooom, Eater of CatToys (also CatSources)'

    def add_arguments(self, parser):
        parser.add_argument('age', default=30, help='Age of the data to delete (30 days)')
        parser.add_argument('--delete', action="store_true", help='Whether to actually do the deletion')

    def handle(self, *args, **options):
        usage = "Invalid usage. Usage: : %s age [30.0] [--delete]" % ( argv[1] )

        try:
            age = timedelta(days=float(options['age']))
        except ValueError:
            raise CommandError(usage)

        cutoff = datetime.utcnow() - age
        blocks = Block.objects.filter(block_end__lte=cutoff, reported=True)
        self.stdout.write("Found %d Blocks older than %.1f days" % (blocks.count(), age.total_seconds()/86400.0))
        if blocks.count() > 0:
            for block in blocks:
                frames = Frame.objects.filter(block=block, frametype__in=[Frame.BANZAI_QL_FRAMETYPE, Frame.BANZAI_RED_FRAMETYPE]).values_list('id', flat=True)
                cat_sources = CatalogSources.objects.filter(frame__in=frames)
                self.stdout.write("Found %6d CatalogSources for Block %5d (for %s)" % (cat_sources.count(), block.id, block.body.provisional_name))
                if options['delete']:
                    self.stdout.write("Deleting CatalogSources")
                    cat_sources.delete()

        # XXX Todo purge CatalogSources from non-reported Blocks that are 2 x age old

