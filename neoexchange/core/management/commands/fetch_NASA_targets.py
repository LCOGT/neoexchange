from astrometrics.sources_subs import imap_login, fetch_NASA_targets
from core.views import update_MPC_orbit

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from datetime import datetime
import os

class Command(BaseCommand):
    help = 'Fetch NASA-ARM targets from an email folder'

    def handle(self, *args, **options):
        username = os.environ.get('NEOX_EMAIL_USERNAME','')
        password = os.environ.get('NEOX_EMAIL_PASSWORD','')
        if username != '' and password != '':
            self.stdout.write("==== Fetching NASA/ARM targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
            mailbox = imap_login(username, password)
            if mailbox:
                NASA_targets = fetch_NASA_targets(mailbox, folder="NASA-ARM")
                for obj_id in NASA_targets:
                    self.stdout.write("Reading NASA/ARM target %s" % obj_id)
                    update_MPC_orbit(obj_id, origin='N')
                mailbox.close()
                mailbox.logout()
