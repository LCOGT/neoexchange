
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
            '--old',
            default=False,
            help='When set to True the code updates all NEOs apart of QuerySet that includes active NEOs from the sources provided. The default is set to False to not update old NEOs.'
        )
            
        parser.add_argument(
            '--time',
            type=int,
            choices=[0, 10800, 21600, 32400, 43200, 54000, 64800, 75600, 86400, 129600, 172800],
            default=43200,           
            help='Updates objects depending on number of seconds past the objects original update. This should also allow other integer values. Default is set to 43200 seconds (12 hours). 3hrs=10800, 6hrs=21600, 9hrs=32400, 12hrs=43200, 15hrs=54000, 18hrs=64800, 21hrs=75600, 24hrs=86400, 36hrs=129600, 48hrs=172800'
        )


    def handle(self, *args, **options):
        time = options['time'] 
        old = options['old']

        if options['sources']=='allneos':
            origins = ['M', 'N', 'S', 'D', 'G', 'A', 'R', 'L']
        elif options['sources']=='nasa':
            origins = ['G', 'N']
        elif options['sources']=='radar':
            origins = ['G','A','R']
        elif options['sources']=='objects':
            origins = ['N', 'S', 'D', 'G', 'A', 'R']
        else:
            origins = ['N', 'S', 'D', 'G', 'A', 'R']         
	   
        self.update_neos(origins, time, old)
                    
            
    def update_neos(self, origins=['N', 'S', 'D', 'G', 'A', 'R'], time=43200, old=False):
        """'origins' are the list of origins to be updated. The default list contains every origin except MPC and LCO. 
        'time' is in seconds and its default is set to 43200 seconds(12 hours). 
        'old' allows all NEOs apart of the Query Set to be updated. Its default value is set to False"""
        
        time_now = datetime.utcnow()
        self.stdout.write("==== Preparing to Updating Targets %s ====" % (time_now.strftime('%Y-%m-%d %H:%M')))
        targets = Body.objects.filter(origin__in=origins, active=True)
        self.stdout.write("Length of target query set to check %d" %(targets.count()))
        were_updated = []

        for target in targets:
            time_diff = float(timedelta.total_seconds(time_now - target.update_time))
            print target

            
            if target.updated == False:
                self.stdout.write("+++ Checking Target that has not been Updated +++")
                self.stdout.write("Reading NEO {name} from {origin}".format(name=target.name, origin=target.origin))
                #update_MPC_orbit(target.name, target.origin)
                # Wait between 10 and 20 seconds
                #delay = random_delay(10, 20)
                were_updated.append(target)
                
            elif target.updated == True and old == True:
                self.stdout.write("+++ Updating Old Target +++")
                self.stdout.write("Reading NEO {name} from {origin} /// Last updated on {updated}".format(name=target.name, origin=target.origin, updated=target.update_time))
                
                #update_MPC_orbit(target.name, target.origin)
                # Wait between 10 and 20 seconds
                #delay = random_delay(10, 20)
                were_updated.append(target)
                
            elif target.updated == True and time_diff > time and time_diff < 2800000:
                #checks when it has been last updated
                self.stdout.write("+++ Checking Previously Updated Target +++")
                self.stdout.write("Reading NEO {name} from {origin} /// Last updated on {updated}".format(name=target.name, origin=target.origin, updated=target.update_time))
                
                #update_MPC_orbit(target.name, target.origin)
                # Wait between 10 and 20 seconds
                #delay = random_delay(10, 20)
                were_updated.append(target)
                
            else:
                pass
                
        if were_updated == []:
            self.stdout.write("==== No NEOs to be updated ====")
        else:      
            self.stdout.write("==== Updated {number} NEOs ====".format(number=len(were_updated)))

               
                    
