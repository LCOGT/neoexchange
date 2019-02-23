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
import os
from django.core.management.base import BaseCommand, CommandError

from astrometrics.sources_subs import fetch_taxonomy_page
from core.views import update_taxonomy
from core.models import Body
from sty import fg


class Command(BaseCommand):
    help = 'Check Database for objects in need of Taxonomy update'

    def handle(self, *args, **options):
        self.stdout.write("==== Fetching Taxonomy Tables %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        pds_tax = os.path.join('photometrics', 'data', 'taxonomy10.tab.dat')
        new_tax_data = fetch_taxonomy_page(pds_tax)
        bodies = Body.objects.filter(active=True)
        i = 0
        for body in bodies:
            i += 1
            self.stdout.write("{} ==== Updating {} ==== ({} of {}) ".format(datetime.now().strftime('%Y-%m-%d %H:%M'), body.current_name(), i, len(bodies)))
            resp = update_taxonomy(body, new_tax_data, dbg=False)
            if resp:
                msg = fg.green + "Updated {} Taxonomic measurements for {}".format(resp, body.name) + fg.rs
            elif resp is 0:
                msg = fg.li_blue + "All Taxonomy for {} has been previously recorded.".format(body.name) + fg.rs
            else:
                msg = "No Taxonomy available for {}".format(body.name)
            self.stdout.write(msg)
