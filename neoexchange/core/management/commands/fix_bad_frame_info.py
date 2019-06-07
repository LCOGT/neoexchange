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

from astrometrics.ephem_subs import LCOGT_domes_to_site_codes
from core.models import Frame, SITE_CHOICES

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from datetime import datetime

camera_mapping = {
                    'fl03': ('lsc', 'domb', '1m0a'),
                    'fl04': ('lsc', 'domc', '1m0a'),
                    'fl05': ('elp', 'doma', '1m0a'),
                    'fs02': ('ogg', 'clma', '2m0a'),
                    'kb16': ('sqa', 'doma', '0m8a'),
                    'kb27': ('ogg', 'clma', '0m4b'),
                    'kb29': ('tfn', 'aqwa', '0m4a'),
                    'kb70': ('cpt', 'doma', '1m0a'),
                    'kb71': ('coj', 'domb', '1m0a'),
                    'kb76': ('cpt', 'domb', '1m0a'),
                    'kb78': ('lsc', 'doma', '1m0a'),
                    'kb82': ('ogg', 'clma', '0m4c'),
                    'kb84': ('coj', 'clma', '0m4b'),
                    'nres': ('sqa', 'doma', '0m8a'),
                    'kb74': ('elp','doma','1m0a')
                }

class Command(BaseCommand):
    help = 'Fix Frames which have incorrect frametype and MPC codes'

    def handle(self, *args, **options):
        self.stdout.write("==== Fetching bad Frames %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))

        # We assume that if value of MPC code is an LCOGT site, this is wrong.
        sites = [site[0] for site in SITE_CHOICES]
        frames = Frame.objects.filter(sitecode__in=sites)

        for frame in frames:
            # Look up site info from camera mapping
            site_info = camera_mapping[frame.instrument]
            mpc_code = LCOGT_domes_to_site_codes(*site_info)
            frame.sitecode = mpc_code
            frame.frametype = Frame.SINGLE_FRAMETYPE
            frame.save()
            self.stdout.write("Updating %s" % frame)
