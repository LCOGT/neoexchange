import os
from sys import argv
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.forms import model_to_dict

from core.models import Frame
from core.management.commands import download_archive_data, pipeline_astrometry
from astrometrics.ephem_subs import determine_rates_pa
from photometrics.catalog_subs import get_fits_files, sort_rocks, find_first_last_frames

class Command(BaseCommand):

    help = 'Download and pipeline process data from the LCO Archive'

    def add_arguments(self, parser):
        default_path = os.path.join(os.path.sep, 'data', 'eng', 'rocks')
        parser.add_argument('--date', action="store", default=datetime.utcnow(), help='Date of the data to download (YYYYMMDD)')
        parser.add_argument('--proposal', action="store", default="LCO2019B-023", help='Proposal code to query for data (e.g. LCO2019B-023)')
        parser.add_argument('--datadir', action="store", default=default_path, help='Path for processed data (e.g. /data/eng/rocks)')
        parser.add_argument('--mtdlink_file_limit', action="store", type=int, default=9, help='Maximum number of images for running mtdlink')
        parser.add_argument('--keep-temp-dir', action="store_true", help='Whether to remove the temporary directories')
        parser.add_argument('--object', action="store", help="Which object to analyze")
        parser.add_argument('--skip-download', action="store_true", help='Whether to skip downloading data')


    def handle(self, *args, **options):
        usage = "Incorrect usage. Usage: %s --date [YYYYMMDD] --proposal [proposal code] --data-dir [path]" % ( argv[1] )

        self.stdout.write("==== Download and process astrometry %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))

        if type(options['date']) != datetime:
            try:
                obs_date = datetime.strptime(options['date'], '%Y%m%d')
            except ValueError:
                raise CommandError(usage)
        else:
            obs_date = options['date']

        obs_date = obs_date.strftime('%Y%m%d')
        proposal = options['proposal']
        dataroot = options['datadir']
        verbose = True
        if options['verbosity'] < 1:
            verbose = False

        if not os.path.exists(dataroot):
            self.stdout.write("Creating download location: %s" % dataroot)
            try:
                os.makedirs(dataroot)
            except:
                msg = "Error creating output path %s" % dataroot
                raise CommandError(msg)

# Step 1: Download data

        if options['skip_download']:
            self.stdout.write("Skipping download data for %s from %s" % ( obs_date, proposal ))
        else:
            self.stdout.write("Download data for %s from %s" % ( obs_date, proposal ))
            call_command('download_archive_data', '--date', obs_date, '--proposal', proposal, '--datadir', dataroot )


        # Append date to the data directory
        dataroot = os.path.join(dataroot, obs_date)

# Step 2: Sort data into directories per-object

        fits_files = get_fits_files(dataroot)
        self.stdout.write("Found %d FITS files in %s" % (len(fits_files), dataroot) )
        objects = sort_rocks(fits_files)
        print(objects)

# Step 3: For each object:
        for rock in objects:
# Skip if a specific object was specified on the commandline and this isn't it
            if options['object'] is not None:
                if options['object'] not in rock:
                    continue
            datadir = os.path.join(dataroot, rock)
            self.stdout.write('Processing target %s in %s' % (rock, datadir))

# Step 3a: Check data is in DB
            fits_files = get_fits_files(datadir)
            self.stdout.write("Found %d FITS files in %s" % (len(fits_files), datadir) )
            first_frame, last_frame = find_first_last_frames(fits_files)
            if first_frame is None or last_frame is None:
                self.stderr.write("Couldn't determine first and last frames, skipping target")
                continue
            self.stdout.write("Timespan %s->%s" % ( first_frame.midpoint, last_frame.midpoint))
# Step 3b: Calculate mean PA and speed
            if first_frame.block:
                body = first_frame.block.body
                if body.epochofel:
                    elements = model_to_dict(body)
                    min_rate, max_rate, pa, deltapa = determine_rates_pa(first_frame.midpoint, last_frame.midpoint, elements, first_frame.sitecode)

# Step 3c: Run pipeline_astrometry
                    mtdlink_args = "datadir=%s pa=%03d deltapa=%03d minrate=%.3f maxrate=%.3f" % (datadir, pa, deltapa, min_rate, max_rate)
                    skip_mtdlink = False
                    keep_temp_dir = False
                    if len(fits_files) > options['mtdlink_file_limit']:
                        self.stdout.write("Too many frames to run mtd_link")
                        skip_mtdlink= True
                    if options['keep_temp_dir']:
                        keep_temp_dir = True
# Compulsory arguments need to go here as a list
                    mtdlink_args = [datadir, pa, deltapa, min_rate, max_rate]

# Optional arguments go here, minus the leading double minus signs and with
# hyphens replaced by underscores for...reasons.
# e.g. '--keep-temp-dir' becomes 'temp_dir'
                    mtdlink_kwargs = {  'temp_dir' : os.path.join(datadir, 'Temp'),
                                        'skip_mtdlink' : skip_mtdlink,
                                        'keep_temp_dir' : keep_temp_dir
                                     }
                    self.stdout.write("Calling pipeline_astrometry with: %s %s" % (mtdlink_args, mtdlink_kwargs))
                    status = call_command('pipeline_astrometry', *mtdlink_args , **mtdlink_kwargs)
                    self.stderr.write("\n")
                else:
                    self.stderr.write("Object %s does not have updated elements" % body.current_name() )
            else:
                self.stderr.write("No Block found for the object")

        self.stdout.write("\n==== Completed download and process astrometry %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
