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
from core.views import update_MPC_orbit, update_MPC_obs, refit_with_findorb, save_and_make_revision
from core.models import Body


class Command(BaseCommand):
    help = 'Update Characterization Targets'

    def handle(self, *args, **options):
        bodies = Body.objects.filter(active=True).exclude(origin='M')
        i = f = 0
        for body in bodies:
            self.stdout.write("{} ==== Updating {} ==== ({} of {}) ".format(datetime.now().strftime('%Y-%m-%d %H:%M'), body.current_name(), i+1, len(bodies)))
            # Get new observations from MPC
            measures = update_MPC_obs(body.current_name())

            # If we have no new measures, or previously flagged as fast
            # Check if close, change 'fast_moving' flag accordingly
            if not measures or body.fast_moving:
                body_elements = model_to_dict(body)
                eph = compute_ephem(datetime.now(), body_elements, 500, perturb=False, detailed=True)
                speed = eph[0][4]
                delta = eph[3]
                if speed >= 5 or delta <= 0.1:
                    fast_flag = {'fast_moving': True}
                else:
                    fast_flag = {'fast_moving': False}
                if body.fast_moving != fast_flag['fast_moving']:
                    updated = save_and_make_revision(body, fast_flag)
                    body.refresh_from_db()
                    if updated:
                        self.stdout.write("Set 'Fast_moving' to {} for {}.".format(body.fast_moving, body.current_name()))

            # If new observations, use them to refit elements with findorb.
            # Will update epoch to date of most recent obs.
            # Will only update if new epoch closer to present than previous.
            if measures or body.fast_moving:
                refit_with_findorb(body.id, 500)
                f += 1
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
        self.stdout.write("{} ==== Updating Complete: {} of {} Objects Updated ====".format(datetime.now().strftime('%Y-%m-%d %H:%M'), f, i))
