"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2021-2021 LCO

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

from core.views import schedule_GNSS_satellites


class Command(BaseCommand):
    help = 'Schedule GNSS (GPS, Glonass etc)_satellites for observations '

    def add_arguments(self, parser):
        parser.add_argument('sitecode', action="store", default=None, help="Sitecode to schedule for")
        parser.add_argument('date', default=datetime.utcnow(), type=datetime.fromisoformat, help='Date to schedule for (YYYYMMDDTHH)')
        parser.add_argument('--execute', default=False, action='store_true', help='Execute observations on the network')


    def handle(self, *args, **options):
        self.stdout.write("==== Scheduling GNSS satellites %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))

        print(options)
        num_scheduled = schedule_GNSS_satellites(options['sitecode'], options['date'], options['execute'])

        self.stdout.write("Scheduled %d satellites" % num_scheduled)

        self.stdout.write("==== Finished scheduling GNSS satellites %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
    
