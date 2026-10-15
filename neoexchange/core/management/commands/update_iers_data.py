"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2026 LCO

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

from astropy.utils import iers
from astropy.utils.data import download_file, import_file_to_cache
from django.core.management.base import BaseCommand, CommandError

from astrometrics.time_subs import IERS_A_URL


class Command(BaseCommand):
    help = 'Download the latest IERS-A Earth orientation table (finals2000A.all) into the astropy cache for UT1-UTC lookups'

    def handle(self, *args, **options):
        self.stdout.write("==== Updating IERS-A table %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        sources = [IERS_A_URL, iers.conf.iers_auto_url_mirror]
        # Download to a temporary file and check it parses before putting it in
        # the cache, so a truncated/bad download can't replace a good table.
        try:
            temp_file = download_file(IERS_A_URL, sources=sources, cache=False)
            table = iers.IERS_A.read(temp_file)
        except Exception as e:
            raise CommandError("Unable to download a valid IERS-A table from %s: %s" % (" or ".join(sources), e))
        import_file_to_cache(IERS_A_URL, temp_file, remove_original=True)
        self.stdout.write("Cached IERS-A table with %d rows: MJD %.0f-%.0f, predictions from MJD %.0f" %
                          (len(table), table['MJD'][0].value, table['MJD'][-1].value, table.meta['predictive_mjd']))
