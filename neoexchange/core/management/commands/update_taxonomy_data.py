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
from django.conf import settings
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
        pds_tax = os.path.join(settings.BASE_DIR, 'photometrics', 'data', 'taxonomy10.tab.dat')
        sdss_tax = os.path.join(settings.BASE_DIR, 'photometrics', 'data', 'sdsstax_ast_table.tab.dat')
        pds_tax_data = fetch_taxonomy_page(pds_tax)
        sdss_tax_data = fetch_taxonomy_page(sdss_tax)
        bodies = Body.objects.filter(active=True)
        i = 0
        c = 0
        for body in bodies:
            i += 1
            self.stdout.write("{} ==== Updating {} ==== ({} of {}) ".format(datetime.now().strftime('%Y-%m-%d %H:%M'), body.current_name(), i, len(bodies)))
            resp = update_taxonomy(body, pds_tax_data, dbg=False)
            resp2 = update_taxonomy(body, sdss_tax_data, dbg=False)
            if resp + resp2:
                msg = fg.green + "Updated {} Taxonomic measurements for {}".format(resp + resp2, body.current_name()) + fg.rs
                c += 1
            elif resp == 0 or resp2 == 0:
                msg = fg.li_blue + "All Taxonomies for {} have been previously recorded.".format(body.current_name()) + fg.rs
            else:
                msg = "No Taxonomies available for {}".format(body.current_name())
            self.stdout.write(msg)
        self.stdout.write("{} ==== Updated Taxonomies for {} of {} objects.".format(datetime.now().strftime('%Y-%m-%d %H:%M'), c, i))
