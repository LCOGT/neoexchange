
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
         
            
    def update_neos(origins=['N', 'S', 'D', 'G', 'A', 'R']):
        self.stdout.write("==== Updating Targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        targets = Body.objects.filter(origin=origins).order_by('-ingest')
           
        if targets.updated == False:
            self.stdout.write("Reading NEO %s from %s" % targets.name, targets.origin)
            update_MPC_orbit(targets.name, targets.origin)
            # Wait between 10 and 20 seconds
            delay = random_delay(10, 20)

        elif targets.updated == True:
        #checks when it has been last updated
    
            if targets.update_time >= datetime.now() - timedelta(hours=options['time']) and targets.update_time <= datetime.now() - timedelta(hours=24):
            #if object has not been updated within 
                self.stdout.write("Reading NEO %s from %s" % targets.name, targets.origin)
                update_MPC_orbit(targets.name, targets.origin)
                # Wait between 10 and 20 seconds
                delay = random_delay(10, 20)
                
            elif targets.update_time >= datetime.now() - timedelta(hours=48):
            #if object has not been updated in 48 hours
                self.stdout.write("Reading NEO %s from %s" % targets.name, targets.origin)
                update_MPC_orbit(targets.name, targets.origin)
                # Wait between 10 and 20 seconds
                delay = random_delay(10, 20)
                    
                    

    def handle(self, *args, **options):
        if options['allneos']:
            allneos = ['M', 'N', 'S', 'D', 'G', 'A', 'R', 'L']
            update_neos(origins=allneos)
        elif options['objects']:
            objects = ['N', 'S', 'D', 'G', 'A', 'R']
            update_neos(origins=objects)
        elif options['nasa']:
            nasa = ['G', 'N']
            update_neos(origins=nasa)
        elif options['radar']:
            radar = ['G','A','R']
            update_neos(origins=radar)
        else:
            pass

