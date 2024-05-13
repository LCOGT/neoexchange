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

from astrometrics.sources_subs import fetch_NEOCP, parse_NEOCP_extra_params, random_delay
from core.views import update_NEOCP_orbit, update_NEOCP_observations

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from datetime import datetime


class Command(BaseCommand):
    help = 'Check NEOCP for objects in need of follow up'

    def handle(self, *args, **options):
        self.stdout.write("==== Fetching NEOCP targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        neocp_page = fetch_NEOCP()
        obj_ids = parse_NEOCP_extra_params(neocp_page)
        if obj_ids:
            self.stdout.write("==== Found %s NEOCP targets ====" % len(obj_ids))
            for obj_id in obj_ids:
                obj_name = obj_id[0]
                obj_extra_params = obj_id[1]
                self.stdout.write("Reading NEOCP target %s" % obj_name)
                resp = update_NEOCP_orbit(str(obj_name), obj_extra_params)
                if resp:
                    self.stdout.write(resp)
                resp = update_NEOCP_observations(str(obj_name), obj_extra_params)
                if resp:
                    self.stdout.write(resp)
                random_delay(2, 5)
        else:
            self.stdout.write("==== Could not find NEOCP or PCCP pages ====")
