
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
            '--sources',
            type=str,
            choices=['allneos', 'nasa', 'radar', 'objects'],
            default='objects',
            help='Updates NEOs by origin source. "allneos" updates all NEOs, "nasa" updates origins assosiated with NASA, "radar" updates NEOs being followed by radar origins, "objects" updates all but MPC and LCO objects.'
        )

        parser.add_argument(
            '--time',
            type=int,
            choices=range(1, 25),
            default=12,           
            help='Updates objects depending on number of hours past the objects original update'
        )


    def handle(self, *args, **options):
        time = options['time'] 

        if options['sources']=='allneos':
            origins = ['M', 'N', 'S', 'D', 'G', 'A', 'R', 'L']
            print "ALL THE NEOS!!!!"
        elif options['sources']=='nasa':
            origins = ['G', 'N']
            print "yes I do like nasa"
        elif options['sources']=='radar':
            origins = ['G','A','R']
            print "I am going through radar"
        elif options['sources']=='objects':
            origins = ['N', 'S', 'D', 'G', 'A', 'R']
            print "not MPC not LCO"
        else:
            origins = ['N', 'S', 'D', 'G', 'A', 'R']
            print "I've tried everything"         
	   
        self.update_neos(origins, time)
                    
            
    def update_neos(self, origins=['N', 'S', 'D', 'G', 'A', 'R'], time=12):
        """Origins are the list of origins to be updated. The default list contains every origin except MPC and LCO. Time is in hours and its default is set to 12 hours."""
        self.stdout.write("==== Updating Targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        targets = Body.objects.filter(origin__in=origins, active=True)
        self.stdout.write("Length of target query set %d" %(targets.count()))
        for target in targets:
            print target
            time_now = datetime.utcnow()
            timediff = timedelta(hours=time)
            oneday = timedelta(hours=24)
            if target.updated == False:
                self.stdout.write("Reading NEO {name} from {origin}".format(name=target.name, origin=target.origin))
                #update_MPC_orbit(target.name, target.origin)
                # Wait between 10 and 20 seconds
                #delay = random_delay(10, 20)
                
            elif target.updated == True and time_now - target.update_time >= time_now - timediff and time_now - target.update_time <= time_now - oneday:
                #checks when it has been last updated
                self.stdout.write("==== Checking Previously Updated Targets ====")
                self.stdout.write("Reading NEO {name} from {origin}".format(name=target.name, origin=target.origin))
                
                #update_MPC_orbit(target.name, target.origin)
                # Wait between 10 and 20 seconds
                #delay = random_delay(10, 20)
                     
            else:
                pass
                
        self.stdout.write("==== No NEOs to be updated ====")


               
                    
