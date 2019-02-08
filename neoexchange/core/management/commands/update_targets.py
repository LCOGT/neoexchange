"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2017-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from astrometrics.sources_subs import random_delay
from core.views import update_MPC_orbit, update_neos
from core.models import Body

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'This command updates objects that have been ingested in the last three months, that ' \
           'have not been updated within 2 days and that are not from the Minor Planet Center or LCO ' \
           'using default settings. There are three optional arguments that have choices that specify ' \
           'what you would like to update; sources, ingest_time, update_age, and date.'

    def __init__(self):
        super(Command, self).__init__()
        
    def add_arguments(self, parser):
        parser.add_argument(
            '--sources',
            type=str,
            choices=['allneos', 'nasa', 'radar', 'objects'],
            default='objects',
            help='Updates NEOs by origin source. "allneos" updates all NEOs, "nasa" updates '
                 'origins associated with NASA, "radar" updates NEOs being followed by radar origins, '
                 '"objects" updates all but MPC and LCO objects, "M" is the Minor Planet Center, '
                 '"N" is NASA, "S" is Spacewatch, "D" is NEODSYS, "G" is Goldstone,"A" is Arecibo, '
                 '"R" is both Goldstone and Aricebo, "L" is LCO, "Y" is Yarkovsky.'
        )
        
        parser.add_argument(
            '--ingest_time',
            type=int,
            default=90,
            help='"ingest_time" is the number of days from the "date" given in the command line. '
                 'The command takes in a integer value of days. The default value is 90 days.'
        )

        parser.add_argument(
            '--update_age',
            type=int,
            default=2,
            help='"update_age" is the time in days from the "date" given in the command line. '
                 'The command takes in a integer value of hours. The default value is 2 days. '
        )
        
        parser.add_argument(
            '--date',
            type=str,
            default=datetime.utcnow(),
            help='"date" is the starting date that the updates will be centered around. '
                 'The default is datetime.datetime.utcnow(). If a date is given in the command '
                 'it must be a string in the format of "%y-%m-%d %H:%M:%S"; any other format '
                 'will trigger a ValueError.'
        )

    def handle(self, *args, **options):
        time = options['update_age'] 
        date = options['date']
        old = options['ingest_time'] 

        if options['sources'] == 'allneos':
            origins = ['M', 'N', 'S', 'D', 'G', 'A', 'R', 'L', 'Y']
        elif options['sources'] == 'nasa':
            origins = ['G', 'N']
        elif options['sources'] == 'radar':
            origins = ['G', 'A', 'R']
        elif options['sources'] == 'objects':
            origins = ['N', 'S', 'D', 'G', 'A', 'R', 'Y']
        else:
            origins = ['N', 'S', 'D', 'G', 'A', 'R', 'Y']

        update_neos(origins=origins, updated_time=time, ingest_limit=old, start_time=date)
