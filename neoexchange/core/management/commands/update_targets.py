from argparse import ArgumentParser as parser
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from astrometrics.sources_subs import random_delay
from core.views import update_MPC_orbit




class Command(BaseCommand):
    help = 'Updates objects that have not been updated within 12 hours that are not from the Minor Planet Center or LCO.'

    def add_arguments(self, parser):
        parser.add_arguments(
            'origin',
            type=str,
            choices=['all', 'nasa', 'radar', 'objects'],
            default='objects',
            help='Updates object depending on choice: all=all origins, nasa=NASA affiliated origins, radar=radar observatory origins, objects=origins excluding MPC and LCO'
        )
        
        parser.add_arguments(
            'time',
            type=int,
            choices=range(0, 24),
            default=12,
            help='Updates objects depending on number of hours past the objects original update'
        )
            
    def handle(self, *args, **options):
    
        for Body.objects.origin in options['origin']:
        
            if Body.updated == False:
                self.stdout.write("==== Updating Targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
                update_MPC_orbit(obj_id, origin=Body.objects.origin)
                # Wait between 10 and 20 seconds
                delay = random_delay(10, 20)
                self.stdout.write("Slept for %d seconds" % delay)

            elif Body.updated == True:
            #checks when it has been last updated

                if Body.update_time >= datetime.now() - timedelta(hours=options['time']):
                    self.stdout.write("==== Updating Targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
                    update_MPC_orbit(obj_id, origin=Body.objects.origin)
                    # Wait between 10 and 20 seconds
                    delay = random_delay(10, 20)
                    self.stdout.write("Slept for %d seconds" % delay)
                else:
                    pass
            else:
                pass
       

