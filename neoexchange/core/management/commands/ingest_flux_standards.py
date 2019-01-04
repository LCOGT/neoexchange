"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2018-2019 LCO

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

from core.models import StaticSource
from astrometrics.sources_subs import fetch_flux_standards
from core.views import create_calib_sources

class Command(BaseCommand):
    help = "Ingest the list of ESO Spectrophotometric standards"

    def handle(self, *args, **options):
        self.stdout.write("==== Fetching ESO spectrophotometric standards %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        flux_standards = fetch_flux_standards()
        num_created = create_calib_sources(flux_standards)
        self.stdout.write("=== Created {} new flux standards".format(num_created))
