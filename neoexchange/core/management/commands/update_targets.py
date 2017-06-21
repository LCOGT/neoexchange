
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from astrometrics.sources_subs import random_delay
from core.views import update_MPC_orbit
from core.models import Body



class Command(BaseCommand):
    help = 'Updates objects that have not been updated within 12 hours that are not from the Minor Planet Center or LCO.'

    def add_arguments(self, parser):
        parser.add_argument(
            'origin',
            type=str,
            choices=['allneos', 'nasa', 'radar', 'objects'],
            default='objects',
            narg='?'
            help='Updates object depending on choice: allneo=all origins, nasa=NASA affiliated origins, radar=radar observatory origins, objects=origins excluding MPC and LCO',
            )
        
        parser.add_argument(
            'time',
            type=int,
            choices=range(1, 25),
            default=12,
            narg='?'
            help='Updates objects depending on number of hours past the objects original update',
            )
            
    def handle(self, *args, **options):
        print "I made it here"
        if Body.origin in options['objects']:
        
            origins = ['N', 'S', 'D', 'G', 'A', 'R']
            
            if Body.updated == False:
                self.stdout.write("==== Updating Targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
                update_MPC_orbit(obj_id, origins)
                # Wait between 10 and 20 seconds
                delay = random_delay(10, 20)
                self.stdout.write("Slept for %d seconds" % delay)

            elif Body.updated == True:
            #checks when it has been last updated

                if Body.update_time >= datetime.now() - timedelta(hours=options['time']):
                    self.stdout.write("==== Updating Targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
                    update_MPC_orbit(obj_id, origins)
                    # Wait between 10 and 20 seconds
                    delay = random_delay(10, 20)
                    self.stdout.write("Slept for %d seconds" % delay)

        
        elif Body.origin in options['allneos']:
            
            origins = ['M', 'N', 'S', 'D', 'G', 'A', 'R', 'L']
            
            if Body.updated == False:
                self.stdout.write("==== Updating Targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
                update_MPC_orbit(obj_id, origins)
                # Wait between 10 and 20 seconds
                delay = random_delay(10, 20)
                self.stdout.write("Slept for %d seconds" % delay)

            elif Body.updated == True:
            #checks when it has been last updated

                if Body.update_time >= datetime.now() - timedelta(hours=options['time']):
                    self.stdout.write("==== Updating Targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
                    update_MPC_orbit(obj_id, origins)
                    # Wait between 10 and 20 seconds
                    delay = random_delay(10, 20)
                    self.stdout.write("Slept for %d seconds" % delay)

                
        elif Body.origin in options['nasa']:
            
            origins = ['G', 'N']
            
            if Body.updated == False:
                self.stdout.write("==== Updating Targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
                update_MPC_orbit(obj_id, origins)
                # Wait between 10 and 20 seconds
                delay = random_delay(10, 20)
                self.stdout.write("Slept for %d seconds" % delay)

            elif Body.updated == True:
            #checks when it has been last updated

                if Body.update_time >= datetime.now() - timedelta(hours=options['time']):
                    self.stdout.write("==== Updating Targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
                    update_MPC_orbit(obj_id, origins)
                    # Wait between 10 and 20 seconds
                    delay = random_delay(10, 20)
                    self.stdout.write("Slept for %d seconds" % delay)

                            
        elif Body.origin in options['radar']:
            
            origins = ['G','A','R']
            
            if Body.updated == False:
                self.stdout.write("==== Updating Targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
                update_MPC_orbit(obj_id, origins)
                # Wait between 10 and 20 seconds
                delay = random_delay(10, 20)
                self.stdout.write("Slept for %d seconds" % delay)

            elif Body.updated == True:
            #checks when it has been last updated

                if Body.update_time >= datetime.now() - timedelta(hours=options['time']):
                    self.stdout.write("==== Updating Targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
                    update_MPC_orbit(obj_id, origins)
                    # Wait between 10 and 20 seconds
                    delay = random_delay(10, 20)
                    self.stdout.write("Slept for %d seconds" % delay)


