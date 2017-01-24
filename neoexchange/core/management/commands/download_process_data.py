import os
from sys import argv
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.forms import model_to_dict

from core.models import Frame
from core.management.commands import download_archive_data, pipeline_astrometry
from astrometrics.ephem_subs import compute_ephem
from photometrics.catalog_subs import get_fits_files, sort_rocks

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
            
        self.stdout.write("Download data for %s from %s" % ( obs_date, proposal ))
        call_command('download_archive_data', '--date', obs_date, '--proposal', proposal, '--datadir', dataroot )

        # Append date to the data directory
        dataroot = os.path.join(dataroot, obs_date)

# Step 2: Sort data into directories per-object

        fits_files = get_fits_files(dataroot)
        self.stdout.write("Found %d FITS files in %s" % (len(fits_files), dataroot) )
        objects = sort_rocks(fits_files)

# Step 3: For each object:
        for rock in objects:
            datadir = os.path.join(dataroot, rock)
            self.stdout.write('Processing target %s in %s' % (rock, datadir))

# Step 3a: Check data is in DB
            fits_files = get_fits_files(datadir)
            self.stdout.write("Found %d FITS files in %s" % (len(fits_files), datadir) )
            first_frame = Frame(midpoint=datetime.max)
            last_frame = Frame(midpoint=datetime.min)
            for fits_filepath in fits_files:
                fits_file = os.path.basename(fits_filepath)
                try:
                    frame = Frame.objects.get(filename=fits_file, frametype__in=(Frame.BANZAI_QL_FRAMETYPE, Frame.BANZAI_RED_FRAMETYPE))
                except Frame.DoesNotExist:
                    self.stderr.write("Cannot find Frame DB entry for %s" % fits_file)
                    break
                except Frame.MultipleObjectsReturned:
                    self.stderr.write("Found multiple entries in DB for %s" % fits_file)
                    break
                if frame.midpoint < first_frame.midpoint:
                    first_frame = frame
                if frame.midpoint > last_frame.midpoint:
                    last_frame = frame

            self.stdout.write("Timespan %s->%s" % ( first_frame.midpoint, last_frame.midpoint))
# Step 3b: Calculate mean PA and speed
            if first_frame.block:
                body = first_frame.block.body
                if body.epochofel:
                    elements = model_to_dict(body)

                    first_frame_emp = compute_ephem(first_frame.midpoint, elements, first_frame.sitecode, dbg=False, perturb=True, display=True)
                    first_frame_speed = first_frame_emp[4]
                    first_frame_pa = first_frame_emp[7]

                    last_frame_emp = compute_ephem(last_frame.midpoint, elements, first_frame.sitecode, dbg=False, perturb=True, display=True)
                    last_frame_speed = last_frame_emp[4]
                    last_frame_pa = last_frame_emp[7]

                    self.stdout.write("Speed range %.2f ->%.2f, PA range %.1f->%.1f" % (first_frame_speed , last_frame_speed, first_frame_pa, last_frame_pa))
                    min_rate = min(first_frame_speed, last_frame_speed) - 0.01
                    max_rate = max(first_frame_speed, last_frame_speed) + 0.01
                    # This will probably go squirelly when close to 360.0...
                    pa = (first_frame_pa + last_frame_pa) / 2.0
                    deltapa = max(first_frame_pa,last_frame_pa) - min(first_frame_pa,last_frame_pa)
                    deltapa = max(10.0, deltapa)

# Step 3c: Run pipeline_astrometry
                    mtdlink_options = ""
                    mtdlink_args = "datadir=%s pa=%03d deltapa=%03d minrate=%.3f maxrate=%.3f" % (datadir, pa, deltapa, min_rate, max_rate)
                    if len(fits_files) > 8:
                        self.stdout.write("Too many frames to run mtd_link")
                        mtdlink_options += "--skip-mtdlink"
                    self.stdout.write("Calling pipeline_astrometry with: %s %s" % (mtdlink_args, mtdlink_options))
                    call_command('pipeline_astrometry', datadir, pa, deltapa, min_rate, max_rate, "--temp-dir", os.path.join(datadir, 'Temp'))

                else:
                    self.stderr.write("Object %s does not have updated elements" % body.current_name() )
            else:
                self.stderr.write("No Block found for the object")
