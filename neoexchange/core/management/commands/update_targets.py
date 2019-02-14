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

from astrometrics.sources_subs import random_delay
from core.views import update_MPC_orbit, update_MPC_obs, refit_with_findorb
from core.models import Body


class Command(BaseCommand):
    help = 'Update Characterization Targets'

    def handle(self, *args, **options):
        bodies = Body.objects.filter(active=True).exclude(origin='M')
        i = 0
        for body in bodies:
            self.stdout.write("{} ==== Updating {} ====".format(datetime.now().strftime('%Y-%m-%d %H:%M'), body.current_name()))
            # Get new observations from MPC
            update_MPC_obs(body.current_name())

            # Use new observations to refit elements with findorb.
            # Will update epoch to date of most recent obs.
            # Will not overwrite later elements
            refit_with_findorb(body.id, 500)

            # Pull most recent orbit from MPC
            # Updated infrequently for most targets
            # Will not overwrite later elements
            update_MPC_orbit(body.current_name(), origin=body.origin)

            # add random 10-20s delay to keep MPC happy
            random_delay()
            i += 1

        self.stdout.write("{} ==== Updating Complete: {} Objects Updated ====".format(datetime.now().strftime('%Y-%m-%d %H:%M'), i))
