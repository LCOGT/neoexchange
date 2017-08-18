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
            ' Goldstone,"A" is Arecibo, "R" is both Goldstone and Aricebo, "L" is LCO, "Y" is Yarkovsky.'
        )
        
        parser.add_argument(
            '--ingest_time',
            type=float,
            default=90,
            help='ingest_time is the number of days from the "date" given in the command line.' \
            ' '
        )

        parser.add_argument(
            '--update_age',
            type=int,
            default=48,           
            help='update_age is the '
            'update_age is the time in hours from the "date" given in the command line.' \
            ' '
        )
        
    	parser.add_argument(
         	'--date',
         	type=str,
        	default=datetime.utcnow(),
        	help='date'
	    )




    def handle(self, *args, **options):
        time = options['update_age'] 
        date = options['date']
        old = options['ingest_time'] 
            

        if options['sources']=='allneos':
            origins = ['M', 'N', 'S', 'D', 'G', 'A', 'R', 'L', 'Y']
        elif options['sources']=='nasa':
            origins = ['G', 'N']
        elif options['sources']=='radar':
            origins = ['G','A','R']
        elif options['sources']=='objects':
            origins = ['N', 'S', 'D', 'G', 'A', 'R', 'Y']
        else:
            origins = ['N', 'S', 'D', 'G', 'A', 'R', 'Y']         
	   
        update_neos(origins=origins, updated_time=time, ingest_limit=old, start_time=date)
