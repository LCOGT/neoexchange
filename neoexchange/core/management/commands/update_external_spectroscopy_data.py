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
from dateutil.relativedelta import relativedelta

from django.core.management.base import BaseCommand, CommandError

from astrometrics.sources_subs import fetch_manos_targets, fetch_smass_targets
from core.views import update_previous_spectra


class Command(BaseCommand):
    help = 'Pull in external spectroscopy for Characterization Targets'

    def add_arguments(self, parser):
        parser.add_argument('-a', '--all', action="store_true", help='Download ALL SMASS data. Default: Grab data from the last 6 months.')

    def handle(self, *args, **options):
        if options['all']:
            cut_off = None
        else:
            cut_off = datetime.now().date() - relativedelta(months=6)
            self.stdout.write("==== Checking for new spectra more recent than %s ====" % (cut_off.strftime('%Y-%m-%d %H:%M')))

        self.stdout.write("==== Searching MANOS Tables %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        new_manos_data = fetch_manos_targets(None, cut_off)
        for m_datum in new_manos_data:
            resp = update_previous_spectra(m_datum, 'M', dbg=False)
            if resp:
                msg = "New MANOS data found for %s" % m_datum[0]
                self.stdout.write(msg)
        self.stdout.write("==== Searching SMASS Tables %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        new_smass_data = fetch_smass_targets(None, cut_off)
        for s_datum in new_smass_data:
            resp = update_previous_spectra(s_datum, 'S', dbg=False)
            if resp:
                msg = "New SMASS data found for %s" % s_datum[0]
                self.stdout.write(msg)
