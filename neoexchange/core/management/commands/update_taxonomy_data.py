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

from astrometrics.sources_subs import fetch_taxonomy_page
from core.views import update_taxonomy


class Command(BaseCommand):
    help = 'Check Database for objects in need of Taxonomy update'

    def handle(self, *args, **options):
        self.stdout.write("==== Fetching Taxonomy Tables %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        new_tax_data = fetch_taxonomy_page()
        for tax_id in new_tax_data:
            resp = update_taxonomy(tax_id,dbg=False)
            if resp:
                msg = "Updated Taxonomy for %s" % tax_id[0]
                self.stdout.write(msg)
