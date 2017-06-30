
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
            'objects',
            nargs='?',
            type=str,
            help='Updates objects from specific origins. "objects" updates all but MPC and LCO objects, "allneos" updates all asteroids, "nasa" updates NASA affiated origins, and "radar" updates targets from radar'
        )
        
        parser.add_argument(
            'allneos',
            nargs='?',
            type=str,
            help='Updates objects from specific origins. "objects" updates all but MPC and LCO objects, "allneos" updates all asteroids, "nasa" updates NASA affiated origins, and "radar" updates targets from radar'
        )
        
        parser.add_argument(
            'nasa',
            nargs='?',
            type=str,
            help='Updates objects from specific origins. "objects" updates all but MPC and LCO objects, "allneos" updates all asteroids, "nasa" updates NASA affiated origins, and "radar" updates targets from radar'
        )
        
        parser.add_argument(
            'radar',
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
        time = options['time']
        
        try:
            if options['allneos']:
                origins = ['M', 'N', 'S', 'D', 'G', 'A', 'R', 'L']
                print "ALL OF THE NEOS!!!!"
            elif options['nasa']:
                origins = ['G', 'N']
                print "yes I do like nasa"
            elif options['radar']:
                origins = ['G','A','R']
                print "I am going through radar"
            elif options['objects']:
                origins = ['N', 'S', 'D', 'G', 'A', 'R']
                print "not MPC not LCO"
            else:
                origins = ['N', 'S', 'D', 'G', 'A', 'R']
                print "I've tried everything" 
        except KeyError:
            origins = ['N', 'S', 'D', 'G', 'A', 'R']
            
        self.update_neos(origins, time)
                    
            
    def update_neos(self, origins=['N', 'S', 'D', 'G', 'A', 'R'], time=12):
        """Origins are the list of origins to be updated. The default list contains every origin except MPC and LCO. Time is in hours and its default is set to 12 hours."""
        self.stdout.write("==== Updating Targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        targets = Body.objects.filter(origin__in=origins, active=True)
        self.stdout.write("Length of target query set %d" %(targets.count()))
        for target in targets:
            time_now = datetime.utcnow()
            if target.updated == False:
                self.stdout.write("Reading NEO %s from %s" % target.name, target.origin)
                update_MPC_orbit(target.name, target.origin)
                # Wait between 10 and 20 seconds
                delay = random_delay(10, 20)
            
            elif target.updated == True and target.update_time >= time_now - timedelta(hours=time) and target.update_time <= time_now - timedelta(hours=24):
                #checks when it has been last updated
                self.stdout.write("==== Checking Previously Updated Targets ====")
                self.stdout.write("Reading NEO %s from %s" % target.name, target.origin)
                update_MPC_orbit(target.name, target.origin)
                # Wait between 10 and 20 seconds
                delay = random_delay(10, 20)
                     
            else:
                pass
                
        self.stdout.write("==== No NEOs to be updated ====")
               
                    
