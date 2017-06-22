
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
            '--objects',
            type=str,
            help='Updates objects from origins excluding MPC and LCO'
        )
        
        parser.add_argument(
            '--allneos',
            type=str,
            help='Updates all objects'
        )
        
        parser.add_argument(
            '--nasa',
            type=str,
            help='Updates objects from origins that are NASA affilated'
        )
        
        parser.add_argument(
            '--radar',
            type=str,
            help='Updates objects from radar observatories origins'
        )
        
        parser.add_argument(
            '--time',
            type=int,
            choices=range(1, 25),
            default=12,
            help='Updates objects depending on number of hours past the objects original update'
        )
            
    def handle(self, *args, **options):
        
        if options['objects']:
            origins = ['N', 'S', 'D', 'G', 'A', 'R']
            
            for Body.origin in origins:
            
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
    
            
        elif options['allneos']:
            origins = ['M', 'N', 'S', 'D', 'G', 'A', 'R', 'L']
        
            for Body.origin in origins:

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

                
        elif options['nasa']:
            origins = ['G', 'N']
                
            for Body.origin in origins:             
                        
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
    
                            
        elif options['radar']:
            origins = ['G','A','R']
                
            for Body.origin in origins:
            
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
        
        else:
            origins = ['N', 'S', 'D', 'G', 'A', 'R']
            
            for Body.origin in origins:
            
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
                        
