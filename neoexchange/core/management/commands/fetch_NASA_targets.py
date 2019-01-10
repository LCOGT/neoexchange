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

from datetime import datetime
import os

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from astrometrics.sources_subs import imap_login, fetch_NASA_targets, random_delay
from core.views import update_MPC_orbit

class Command(BaseCommand):
    help = 'Fetch NASA targets from an email folder'

    def handle(self, *args, **options):
        username = os.environ.get('NEOX_EMAIL_USERNAME','')
        password = os.environ.get('NEOX_EMAIL_PASSWORD','')
        if username != '' and password != '':
            self.stdout.write("==== Fetching NASA targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
            mailbox = imap_login(username, password)
            if mailbox:
                NASA_targets = fetch_NASA_targets(mailbox, folder="NASA-ARM")
                for obj_id in NASA_targets:
                    self.stdout.write("Reading NASA target %s" % obj_id)
                    update_MPC_orbit(obj_id, origin='N')
                    # Wait between 10 and 20 seconds
                    delay = random_delay(10, 20)
                    self.stdout.write("Slept for %d seconds" % delay)

                mailbox.close()
                mailbox.logout()
