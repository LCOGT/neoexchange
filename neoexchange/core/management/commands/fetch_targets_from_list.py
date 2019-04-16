"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2017-2019 LCO

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

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from sys import argv
from astrometrics.sources_subs import fetch_list_targets, random_delay
from core.views import update_MPC_orbit
from core.models import ORIGINS

origin_help = '['+', '.join(['"{}":{}'.format(i[0], i[1]) for i in ORIGINS])+']'


class Command(BaseCommand):
    help = 'Fetch targets text file or command line list'

    def add_arguments(self, parser):
        parser.add_argument('list_targets', nargs='+', help='Filenames and/or List of Targets to Ingest')
        parser.add_argument('--origin', help='Origin code for Target list: ' + origin_help)

    def handle(self, *args, **options):
        usage = 'Incorrect usage. Usage must include: --origin ' + origin_help
        origin_choices = [x[0] for x in ORIGINS]
        if options['origin'] not in origin_choices:
            raise CommandError(usage)
        self.stdout.write("==== Fetching New Targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        list_targets = fetch_list_targets(options['list_targets'])
        for obj_id in list_targets:
            self.stdout.write("Reading New Target %s" % obj_id)
            update_MPC_orbit(obj_id, origin=options['origin'])
            # Wait between 10 and 20 seconds
            delay = random_delay(10, 20)
            self.stdout.write("Slept for %d seconds" % delay)
