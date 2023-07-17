from datetime import datetime, timedelta
from dateutil.parser import *
from astropy.io import fits
from django.core.management.base import BaseCommand, CommandError

from core.blocksfind import find_didymos_blocks, find_frames
from core.views import run_astwarp_alignment, run_noisechisel, convert_fits_to_pdf



class Command(BaseCommand):
    help = 'Generates stacked and noise chiseled outputs for Blocks. Generates pdf of final output file.'

    def add_arguments(self, parser):
        parser.add_argument('start_date', help='Start date (YYYYMMDD-HH:MM)')
        parser.add_argument('end_date', help='End date (YYYYMMDD-HH:MM)')
        parser.add_argument('days_inc', type=float, help='Increment days')

    def handle(self, *args, **options):
        start_date = parse(options['start_date'])
        end_date = parse(options['end_date'])
        date_increment = timedelta(days=options['days_inc']) 

        #find all Blocks between start and end date 
        didymos_blocks = find_didymos_blocks()
        blocks = []
        dates = []
        for block in didymos_blocks:
            if start_date <= block.block_start and end_date >= block.block_end:
                blocks.append(block)
                dates.append(block.block_start)

        #check if number of Blocks >0
        if len(blocks) is 0:
            raise CommandError('There are no blocks between start and end date.')

        current_time = start_date
        while current_time <= end_date:
            self.stdout.write(current_time.strftime('%Y-%m-%d %H:%M'))
            current_time += date_increment

            #find closest Block in time to current_time
            block_start = min(dates, key=lambda d: abs(d - current_time))
            index = dates.index(block_start)
            block = blocks[index]

            #find Frames for Block
            frames = find_frames(block)
            filter_frames = frames.order_by('filter').distinct('filter')

            #check if >3 and <10 and same filter
            if len(frames)>3 and len(frames)<10 and filter_frames.count()==1:
                #set up working directory for Block, check to see if we are modifying original files, if yes make a copy of all frames

                #make a record of stack midpoint, stack total exposure time, and moon fraction (need to get from fits header)
                midpoint = block.block_start + (block.block_end - block.block_start)/2
                total_exptime = 0
                moon_fractions = []
                for frame in frames:
                    total_exptime = total_exptime + frame.exptime
                    hdulist = fits.open(frame.filename)
                    header = hdulist['SCI'].header
                    moon_fractions.append(header['MOONFRAC'])
                avg_moon_frac = sum(moon_fractions)/len(moon_fractions)

                #call run_astwarp_alignment(), and run_noisechisel()
                chiseled_filename, status = run_astwarp_alignment_noisechisel(block, sci_dir, dest_dir)
                #call convert_fits_to_pdf()
                pdf_filename, status = convert_fits_to_pdf(chiseled_filename, dest_dir)

            #later: handle muscat frames in g,r,i,z





