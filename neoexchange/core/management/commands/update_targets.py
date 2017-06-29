
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
            choices=['objects', 'allneos', 'nasa', 'radar'],
            const='objects',
            default='objects',
            nargs='?',
            type=str,
            help='Updates objects from specific origins. "objects" updates all but MPC and LCO objects, "allneos" updates all asteroids, "nasa" updates NASA affiated origins, and "radar" updates targets from radar'
        )
        
        parser.add_argument(
            'time',
            type=int,
            choices=range(1, 25),
            const = 12,
            default=12,
            nargs='?',            
            help='Updates objects depending on number of hours past the objects original update'
        )


    def handle(self, *args, **options):
        try:
            if options['allneos']:
                allneos = ['M', 'N', 'S', 'D', 'G', 'A', 'R', 'L']
                self.update_neos(origins=allneos)
            elif options['objects']:
                objects = ['N', 'S', 'D', 'G', 'A', 'R']
                self.update_neos(origins=objects)
            elif options['nasa']:
                nasa = ['G', 'N']
                self.update_neos(origins=nasa)
            elif options['radar']:
                radar = ['G','A','R']
                self.update_neos(origins=radar)
            else:
                objects = ['N', 'S', 'D', 'G', 'A', 'R']
                self.update_neos(origins=objects)    
        except KeyError:
            objects = ['N', 'S', 'D', 'G', 'A', 'R']
            self.update_neos(origins=objects)
                    
            
    def update_neos(self, origins=['N', 'S', 'D', 'G', 'A', 'R']):
        self.stdout.write("==== Updating Targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        targets = Body.objects.get(origin=origins).order_by('-ingest')
        
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
                
        else:
            self.stdout.write("No NEOs to be updated")

