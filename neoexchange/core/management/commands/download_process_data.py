import os
from sys import argv
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command

from core.management.commands import download_archive_data

class Command(BaseCommand):

    help = 'Download and pipeline process data from the LCO Archive'

    def add_arguments(self, parser):
        default_path = os.path.join(os.path.sep, 'data', 'eng', 'rocks')
        parser.add_argument('--date', action="store", default=datetime.utcnow(), help='Date of the data to download (YYYYMMDD)')
        parser.add_argument('--proposal', action="store", default="LCO2016B-011", help='Proposal code to query for data (e.g. LCO2016B-011)')
        parser.add_argument('--datadir', action="store", default=default_path, help='Path for processed data (e.g. /data/eng/rocks)')


    def handle(self, *args, **options):
        usage = "Incorrect usage. Usage: %s --date [YYYYMMDD] --proposal [proposal code] --data-dir [path]" % ( argv[1] )


        if type(options['date']) != datetime:
            try:
                obs_date = datetime.strptime(options['date'], '%Y%m%d')
            except ValueError:
                raise CommandError(usage)
        else:
            obs_date = options['date']

        obs_date = obs_date.strftime('%Y%m%d')
        proposal = options['proposal']
        datadir = options['datadir']
        verbose = True
        if options['verbosity'] < 1:
            verbose = False

        if not os.path.exists(datadir):
            self.stdout.write("Creating download location: %s" % datadir)
            try:
                os.makedirs(datadir)
            except:
                msg = "Error creating output path %s" % datadir
                raise CommandError(msg)

# Step 1: Download data
            
        self.stdout.write("Download data for %s from %s" % ( obs_date, proposal ))
        call_command('download_archive_data', '--date', obs_date, '--proposal', proposal, '--datadir', datadir )

# Step 2: Sort data into directories per-object

# Step 3: For each object:

# Step 3a: Check data is in DB

# Step 3b: Calculate mean PA and speed

# Step 3c: Run pipeline_astrometry
