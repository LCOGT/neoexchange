import logging

from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from astrometrics.sources_subs import random_delay
from core.views import update_MPC_orbit, update_neos
from core.models import Body


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Updates objects that have not been updated within 12 hours that are not from the Minor Planet Center' \
    'or LCO using default settings. There are three optional arguments that have choices that specify what you' \
    'would like to update; sources, old, and time.'

    def __init__(self):
        super(Command, self).__init__()
        
    def add_arguments(self, parser):
        parser.add_argument(
            '--sources',
            type=str,
            choices=['allneos', 'nasa', 'radar', 'objects'],
            default='objects',
            help='Updates NEOs by origin source. "allneos" updates all NEOs, "nasa" updates origins assosiated' \
            ' with NASA, "radar" updates NEOs being followed by radar origins, "objects" updates all but MPC and' \
            ' LCO objects, "M" is the Minor Planet Center, "N" is NASA, "S" is Spacewatch, "D" is NEODSYS, "G" is' \
            ' Goldstone,"A" is Arecibo, "R" is both Goldstone and Aricebo, "L" is LCO.'
        )
        
        parser.add_argument(
            '--old',
            type=bool,
            choices=[True, False],
            default=False,
            help='When set to True the code updates all NEOs apart of QuerySet that are three months or older ' \
            'and NEOs that LCO is activily following from the sources provided. The default is set to False ' \
            'to not update old NEOs.'
        )
            
        parser.add_argument(
            '--never',
            type=bool,
            choices=[True, False],
            default=True,
            help='When set to True the code updates all NEOs apart of the QuerySet that have never been updated.' \
            ' If this is set to False it will not update NEOs that have never been updated.'
        )

        parser.add_argument(
            '--time',
            type=int,
            choices=[0, 10800, 21600, 32400, 43200, 54000, 64800, 75600, 86400, 129600, 172799],
            default=43200,           
            help='Updates objects depending on the time that has passed from the objects original update. ' \
           'The argument given is the number of hours that has passed in seconds. If the objects have been ' \
           'updated then the code looks for objects that have not been updated within the argument time and ' \
           '48 hours. Default is set to 43200 seconds (12 hours). 3hrs=10800, 6hrs=21600, 9hrs=32400, ' \
           '12hrs=43200, 15hrs=54000, 18hrs=64800, 21hrs=75600, 24hrs=86400, 36hrs=129600, 48hrs=172799'
        )
        
    def handle(self, *args, **options):
        time = options['time'] 
       
        if options['old']:
            old = True
        else:
            old = False
            
        if options['never']:
            never = False
        else:
            never = True

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
	   
        update_neos(origins, time, old, never)
