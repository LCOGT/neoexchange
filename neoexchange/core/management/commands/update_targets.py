from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from astrometrics.source_subs import random_delay
from core.views import update_MPC_orbit



def object_update(self, time_diff=12):
    for Body.objects.origin != 'M' or 'L':
        
        if Body.updated == False:
            self.stdout.write("==== Updating Targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
            update_MPC_orbit(obj_id, origin=Body.objects.origin)
            # Wait between 10 and 20 seconds
            delay = random_delay(10, 20)
            self.stdout.write("Slept for %d seconds" % delay)

        elif Body.updated = True:
        #checks when it has been last updated 
            if Body.update_time => datetime.now() - timedelta(hours=time_diff):
                self.stdout.write("==== Updating Targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
                update_MPC_orbit(obj_id, origin=Body.objects.origin)
                # Wait between 10 and 20 seconds
                delay = random_delay(10, 20)
                self.stdout.write("Slept for %d seconds" % delay)
            else:
                pass
        else:
            pass
       

