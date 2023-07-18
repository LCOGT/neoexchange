from datetime import datetime, timedelta
from dateutil.parser import *
from astropy.io import fits
import shutil
import os
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.blocksfind import find_didymos_blocks, find_frames
from core.views import run_astwarp_alignment_noisechisel, convert_fits_to_pdf


class Command(BaseCommand):
    help = 'Generates stacked and noise chiseled outputs for Blocks. Generates pdf of final output file.'

    def add_arguments(self, parser):
        parser.add_argument('start_date', help='Start date (YYYYMMDD-HH:MM)')
        parser.add_argument('end_date', help='End date (YYYYMMDD-HH:MM)')
        parser.add_argument('days_inc', type=float, help='Increment days')
        parser.add_argument('--sci_dir', default=settings.DATA_ROOT, help='Directory where input files are stored')
        parser.add_argument('--dest_dir', default=os.path.join(settings.DATA_ROOT, 'Stacks'), help='Directory where output files will be written')

    def handle(self, *args, **options):
        start_date = parse(options['start_date'])
        end_date = parse(options['end_date'])
        date_increment = timedelta(days=options['days_inc']) 
        sci_dir = options['sci_dir']
        dest_dir = options['dest_dir']

        #find all Blocks between start and end date 
        didymos_blocks = find_didymos_blocks()
        blocks = []
        dates = []
        for block in didymos_blocks:
            if start_date <= block.block_start and end_date >= block.block_end:
                blocks.append(block)
                dates.append(block.block_start)

        #check if number of Blocks >0
        if len(blocks)==0:
            raise CommandError('There are no blocks between start and end date.')

        current_time = start_date
        while current_time <= end_date:
            #self.stdout.write(current_time.strftime('%Y-%m-%d %H:%M'))

            #find closest Block in time to current_time
            block_start = min(dates, key=lambda d: abs(d - current_time))
            index = dates.index(block_start)
            block = blocks[index]

            #remove block from list so it is not repeated --> WIP
            blocks.remove(block)
            dates.remove(block_start)

            #find Frames for Block
            frames = find_frames(block)
            filter_frames = frames.order_by('filter').distinct('filter')

            #check if >3 and <10 and same filter
            if len(frames)>3 and len(frames)<10 and filter_frames.count()==1:
                #set up working directory for Block and make a copy of all frames
                dayobs = block.get_blockdayobs
                input_data_path = os.path.join(sci_dir, dayobs, block.body.current_name()+'_'+block.get_blockuid)
                output_path = os.path.join(dest_dir, 'original_files', dayobs)
                if os.path.exists(output_path) is False:
                    os.makedirs(output_path)
                for frame in frames:
                    shutil.copy(os.path.join(input_data_path,frame.filename), output_path)
                sci_dir_path = output_path
                dest_dir_path = os.path.join(dest_dir, dayobs)

                #make a record of stack midpoint, stack total exposure time, and moon fraction (need to get from fits header)
                midpoint = block.block_start + (block.block_end - block.block_start)/2
                total_exptime = 0
                moon_fractions = []
                for frame in frames:
                    total_exptime = total_exptime + frame.exptime
                    hdulist = fits.open(os.path.join(sci_dir_path, frame.filename))
                    header = hdulist['SCI'].header
                    moon_fractions.append(header['MOONFRAC'])
                avg_moon_frac = round(sum(moon_fractions)/len(moon_fractions), 4)

                self.stdout.write(f'Block Start Time: {block.block_start.strftime("%Y-%m-%d %H:%M")}, Midpoint: {midpoint}, Total Exposure Time: {total_exptime}, Average Moon Fraction: {avg_moon_frac}')

                #call run_astwarp_alignment(), and run_noisechisel()
                chiseled_filename, combined_filename, status = run_astwarp_alignment_noisechisel(block, sci_dir_path, dest_dir_path)
                #call convert_fits_to_pdf()
                pdf_filename_chiseled, status = convert_fits_to_pdf(chiseled_filename, dest_dir_path)
                pdf_filename_combined, status = convert_fits_to_pdf(combined_filename, dest_dir_path)
                self.stdout.write(f'Chiseled filename: {pdf_filename_chiseled}, Combined filename: {pdf_filename_combined}')

            else:
                self.stdout.write(f'Block Start Time: {block.block_start.strftime("%Y-%m-%d %H:%M")} INVALID BLOCK')

            current_time += date_increment

            #later: handle muscat frames in g,r,i,z

#make astropy table with: block_start, block_mid, block_end, exposure time, moon frac, block_uid, input_data_path, output_path then write to csv file
#add logic so we don't repeat blocks
#add logic so that if output filenames aleady exist skip function calls
