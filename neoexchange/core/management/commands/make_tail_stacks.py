from datetime import datetime, timedelta
from dateutil.parser import *
from astropy.io import fits
import shutil
import os
from astropy.table import QTable
from astropy.io import ascii
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.blocksfind import filter_blocks, find_frames, split_light_curve_blocks
from core.views import run_astwarp_alignment_noisechisel, convert_fits, \
    get_didymos_detection, run_make_didymos_chisel_plots, make_annotated_plot
from photometrics.external_codes import run_astmkcatalog, run_asttable, run_didymos_astarithmetic
from photometrics.catalog_subs import reset_database_connection


class Command(BaseCommand):
    help = 'Generates stacked and noise chiseled outputs for Blocks. Generates pdf of final output files.'

    def add_arguments(self, parser):
        width = 1991.0
        height = 911.0
        parser.add_argument('start_date', help='Start date (YYYYMMDD-HH:MM)')
        parser.add_argument('end_date', help='End date (YYYYMMDD-HH:MM)')
        parser.add_argument('days_inc', type=float, help='Increment days')
        parser.add_argument('--sci_dir', default=settings.DATA_ROOT, help='Directory where input files are stored')
        parser.add_argument('--dest_dir', default=os.path.join(settings.DATA_ROOT, 'Stacks'), help='Directory where output files will be written')
        parser.add_argument('--validate_only', type=bool, default=False, help='If set to True, the command will skip the copying, stacking, and chiseling processes. It will instead check for missing data/directories')
        parser.add_argument('--width', type=float, default=width, help=f'Width of chiseled imaged (pixels; default={width:.1f}')
        parser.add_argument('--height', type=float, default=height, help=f'height of chiseled imaged (pixels; default={height:.1f}')

    def handle(self, *args, **options):
        start_date = parse(options['start_date'])
        end_date = parse(options['end_date'])
        date_increment = timedelta(days=options['days_inc']) 
        sci_dir = options['sci_dir']
        dest_dir = options['dest_dir']
        validate_only = options['validate_only']
        width = options['width']
        height = options['height']

        #lists for astropy data table
        blocks_start = []
        blocks_mid = []
        blocks_end = []
        exposure_time = []
        moon_frac = []
        moon_distance = []
        block_uid = []
        input_data_paths = []
        output_data_paths = []
        V_mags = []

        lc_blocks, lc_dates = filter_blocks(None, start_date, end_date, 10, 1000)
        tm_blocks, tm_dates = filter_blocks(None, start_date, end_date, 3, 10)

        all_blocks = lc_blocks + tm_blocks
        all_dates = lc_dates + tm_dates

        #check if number of Blocks >0
        if len(all_blocks)==0:
            raise CommandError('No blocks were found.')

        current_time = start_date
        while current_time <= end_date:
            #self.stdout.write(current_time.strftime('%Y-%m-%d %H:%M'))

            if len(all_blocks) != 0:
                #find closest Block in time to current_time
                block_start_date = min(all_dates, key=lambda d: abs(d - current_time))
                index = all_dates.index(block_start_date)
                block = all_blocks[index]

                #remove block from list so it is not repeated
                del all_blocks[index]
                del all_dates[index]
            else:
                break

            #find Frames in block
            frames, num_banzai, num_neox = find_frames(block)
            #print(frames)

            #later: handle muscat frames in g,r,i,z

            #set up working directory for Block and make a copy of all frames
            dayobs = block.get_blockdayobs
            blockuid = block.get_blockuid
            self.stdout.write(f'DAYOBS: {dayobs}')
            self.stdout.write(f'BLKUID: {blockuid}')
            #self.stdout.write(f'Block Start: {block.block_start}')
            #self.stdout.write(f'Block End: {block.block_end}')
            self.stdout.write(f'Request Number: {block.request_number}')

            #chooses correct input path
            input_data_path_1 = os.path.join(sci_dir, dayobs, block.body.current_name()+'_'+blockuid[0], 'Temp_cvc_multiap')
            if len(blockuid)==2:
                input_data_path_2 = os.path.join(sci_dir, dayobs, block.body.current_name()+'_'+blockuid[1], 'Temp_cvc_multiap')
            output_path = os.path.join(dest_dir, 'original_files', dayobs)
            if os.path.exists(output_path) is False:
                os.makedirs(output_path)
            for frame in frames:
                file_path_1 = os.path.join(input_data_path_1,frame.filename)
                if len(blockuid)==2:
                    file_path_2 = os.path.join(input_data_path_2,frame.filename)
                else:
                    file_path_2 = ''
                if os.path.exists(file_path_1) is False and os.path.exists(file_path_2) is False:
                    if validate_only:
                        self.stdout.write(f'File Not Found: {file_path_1}')
                    frames = frames.exclude(filename = frame.filename)
                    continue
                if os.path.exists(file_path_1):
                    input_data_path = input_data_path_1
                else:
                    input_data_path = input_data_path_2
                if validate_only is False and os.path.exists(os.path.join(output_path,frame.filename)) is False:
                    shutil.copy(os.path.join(input_data_path,frame.filename), output_path)
            sci_dir_path = output_path
            dest_dir_path = os.path.join(dest_dir, dayobs)

            reset_database_connection()

            #make a record of stack midpoint, stack total exposure time, and moon fraction (need to get from fits header)
            if validate_only is False:
                block_start = block.frame_set.filter(frametype=Frame.NEOX_RED_FRAMETYPE).earliest('midpoint').midpoint
                block_end = block.frame_set.filter(frametype=Frame.NEOX_RED_FRAMETYPE).latest('midpoint').midpoint
                midpoint = block_start + (block_end - block_start)/2
                total_exptime = 0
                moon_fractions = []
                moon_dist = []
                for frame in frames:
                    total_exptime = total_exptime + frame.exptime
                    hdulist = fits.open(os.path.join(sci_dir_path, frame.filename))
                    header = hdulist['SCI'].header
                    moon_fractions.append(header['MOONFRAC'])
                    moon_dist.append(header['MOONDIST'])
                avg_moon_frac = round(sum(moon_fractions)/len(moon_fractions), 4)
                avg_moon_dist = round(sum(moon_dist)/len(moon_dist), 4)
                emp = block.body.compute_position(midpoint)
                V_mag = emp[2]

                self.stdout.write(f'Block Start Time: {block_start.strftime("%Y-%m-%d %H:%M")}, Midpoint: {midpoint}, Total Exposure Time: {total_exptime:.1f}, Average Moon Fraction: {avg_moon_frac:.3f}')

                #add values for astropy data table
                blocks_start.append(block_start)
                blocks_mid.append(midpoint)
                blocks_end.append(block_end)
                exposure_time.append(total_exptime)
                moon_frac.append(avg_moon_frac)
                moon_distance.append(avg_moon_dist)
                V_mags.append(V_mag)
                block_uid.append(",".join(blockuid))
                input_data_paths.append(input_data_path)
                output_data_paths.append(output_path)

                #call run_astwarp_alignment(), and run_noisechisel()
                chiseled_filenames, combined_filenames, status = run_astwarp_alignment_noisechisel(block, sci_dir_path, dest_dir_path, width, height)

                reset_database_connection()

                #call convert_fits()
                table = get_ephem(block)

                pdf_filenames_chiseled = []
                pdf_filenames_combined = []
                annotated_plots_combined = []
                catalogs = []
                didymos_ids = []
                for chiseled_filename in chiseled_filenames:
                    if chiseled_filename is not None:
                        filename_base = os.path.basename(chiseled_filename).replace('-combine-superstack-chisel', '')
                        # We assume, apparently correctly, that the WCS in the stack
                        # is inherited from the first frame in the stack. For the
                        # hyperstack, this is inherited from the first superstack
                        # and hence first frame of the Block
                        frame = None
                        try:
                            frame = frames.get(filename__startswith=filename_base)
                        except Frame.DoesNotExist:
                            if 'hyperstack' in filename_base:
                                frame = frames.earliest('midpoint')
                        print(f"Found {frame} for {os.path.basename(chiseled_filename)}")
                        if frame:
                            result_RA, result_DEC = ephem_interpolate(frame.midpoint, table)
                            center_RA = result_RA[0]
                            center_DEC = result_DEC[0]
                        else:
                            center_RA = None
                            center_DEC = None
                        results = run_make_didymos_chisel_plots(chiseled_filename, dest_dir_path, center_RA, center_DEC)
                        pdf_filenames_chiseled.append(results['pdf_filename_chiseled'])
                        catalogs.append(results['catalog_filename'])
                        didymos_ids.append(results['didymos_id'])

                for combined_filename in combined_filenames:
                    if combined_filename is not None:
                        trim_combined_filename, status, new_width, new_height = run_make_crop(combined_filename, dest_dir_path)
                        pdf_filename_combined, status = convert_fits(trim_combined_filename, dest_dir_path)
                        pdf_filenames_combined.append(pdf_filename_combined)
                        jpg_filename_combined, status = convert_fits(trim_combined_filename, dest_dir_path, out_type='jpg')
                        # Make annotated plots
                        if trim_combined_filename is not None:
                            output_plot = make_annotated_plot(trim_combined_filename, width=new_width, height=new_height)
                            annotated_plots_combined.append(output_plot)
                    else:
                        self.stdout.write("combined_filename is None")
                self.stdout.write(f'Chiseled  filename(s): {pdf_filenames_chiseled}')
                self.stdout.write(f'Combined  filename(s): {pdf_filenames_combined}')
                self.stdout.write(f'Annotated filename(s): {annotated_plots_combined}')
                self.stdout.write(f'Catalog(s): {catalogs}')
                self.stdout.write(f'ID(s): {didymos_ids}')
            self.stdout.write('')

            current_time += date_increment

        if validate_only is False:
            #make astropy table and convert to csv file
            table = QTable([blocks_start, blocks_mid, blocks_end, exposure_time, moon_frac, moon_distance, V_mags, block_uid, input_data_paths, output_data_paths],
                    names=('Block Start', 'Block Midpoint', 'Block End', 'Exposure Time', 'Moon Fraction', 'Moon Distance', 'V Magnitude', 'Block UID', 'Input Path', 'Output Path'))
            csv_path = os.path.join(dest_dir, 'didymos_tail_data.csv')
            ascii.write(table, csv_path, format='ecsv', delimiter = ',')