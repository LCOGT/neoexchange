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

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from astrometrics.sources_subs import fetch_arecibo_targets, random_delay
from core.views import update_MPC_orbit

class Command(BaseCommand):
    help = 'Fetch Arecibo target list for the current year'

    def handle(self, *args, **options):
        self.stdout.write("==== Fetching Arecibo targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        radar_targets = fetch_arecibo_targets()
        for obj_id in radar_targets:
            self.stdout.write("Reading Arecibo target %s" % obj_id)
            update_MPC_orbit(obj_id, origin='A')
            # Wait between 10 and 20 seconds
            delay = random_delay(10, 20)
