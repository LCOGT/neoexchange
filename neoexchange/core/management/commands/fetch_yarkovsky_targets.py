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

from datetime import datetime
from os.path import expanduser

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from astrometrics.sources_subs import fetch_yarkovsky_targets, random_delay
from core.views import update_MPC_orbit


class Command(BaseCommand):
    help = 'Fetch Yarkovsky target list for the current month'

    def add_arguments(self, parser):
        parser.add_argument('--targetlist', action="store", default=None, help="File of targets to read (optional; set to 'FTP' to read from JPL site)")
        parser.add_argument('yark_targets', nargs='*', help='List of Yarkovsky targets to ingest')

    def handle(self, *args, **options):
        self.stdout.write("==== Fetching Yarkovsky targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))

        targets = []
        yark_targets = []
        if options['targetlist'] is not None:
            if options['targetlist'] == 'FTP':
                targets = None
            elif options['targetlist'].startswith('ftp://'):
                targets = options['targetlist']
            else:
                with open(expanduser(options['targetlist'])) as f:
                    targets = f.readlines()

            yark_targets = fetch_yarkovsky_targets(targets)
        yark_targets += options['yark_targets']
        for obj_id in yark_targets:
            self.stdout.write("Reading Yarkovsky target %s" % obj_id)
            update_MPC_orbit(obj_id, origin='Y')
            # Wait between 10 and 20 seconds
            delay = random_delay(10, 20)
            self.stdout.write("Slept for %d seconds" % delay)
