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

from astrometrics.sources_subs import fetch_previous_NEOCP_desigs
from core.views import update_crossids

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from datetime import datetime


class Command(BaseCommand):
    help = 'Update objects for new cross-identifications from the Previous NEO Confirmation Page Objects page'

    def handle(self, *args, **options):
        self.stdout.write("==== Updating Cross-IDs %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        objects = fetch_previous_NEOCP_desigs()
        for obj_id in objects:
            resp = update_crossids(obj_id, dbg=False)
            if resp:
                msg = "Updated crossid for %s" % obj_id
                self.stdout.write(msg)
