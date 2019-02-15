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

from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.forms.models import model_to_dict
import pyslalib.slalib as S
from math import degrees

from astrometrics.sources_subs import random_delay
from astrometrics.ephem_subs import compute_ephem
from core.views import update_MPC_orbit, update_MPC_obs, refit_with_findorb
from core.models import Body


class Command(BaseCommand):
    help = 'Update Characterization Targets'

    def handle(self, *args, **options):
        bodies = Body.objects.filter(active=True).exclude(origin='M')
        i = 0
        for body in bodies:
            self.stdout.write("{} ==== Updating {} ==== ({} of {}) ".format(datetime.now().strftime('%Y-%m-%d %H:%M'), body.current_name(), i+1, len(bodies)))
            # Get new observations from MPC
            measures = update_MPC_obs(body.current_name())

            # If new observations, use them to refit elements with findorb.
            # Will update epoch to date of most recent obs.
            # Will only update if new epoch closer to present than previous.
            if measures:
                refit_with_findorb(body.id, 500)
                body.refresh_from_db()

            # If new obs pull most recent orbit from MPC
            # Updated infrequently for most targets
            # Will not overwrite later elements
            if measures or abs(body.epochofel-datetime.now()) >= timedelta(days=200):
                update_MPC_orbit(body.current_name(), origin=body.origin)
                body.refresh_from_db()

            # add random 10-20s delay to keep MPC happy
            random_delay()
            i += 1
        self.stdout.write("{} ==== Updating Complete: {} Objects Updated ====".format(datetime.now().strftime('%Y-%m-%d %H:%M'), i))
