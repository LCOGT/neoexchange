"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2024-2024 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

import warnings
from glob import glob
import os
import sys
import time
import tempfile
import shutil
from datetime import datetime
from itertools import groupby

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from astropy.wcs import FITSFixedWarning

from core.models import StaticSource, Block, Frame
from core.views import run_hotpants_subtraction, determine_images_and_catalogs
from photometrics.image_subs import determine_reffield_for_block, determine_reference_frame_for_block
from photometrics.catalog_subs import funpack_fits_file, make_object_directory

class Command(BaseCommand):
    help = "Perform DIA subtraction "

    def add_arguments(self, parser):
        parser.add_argument('blocknum', type=int, default=None, help='Block (request number) to analyze')
        parser.add_argument('datadir', action="store", default=None, help='Path for processed data (e.g. /data/eng/rocks)')
        parser.add_argument('--filter', type=str, default='', help='Filter to analyze. Default is all unique filters')
        parser.add_argument('--execute', action="store_true", help="Whether to execute the subtraction")

    def handle(self, *args, **options):
        warnings.simplefilter("ignore", FITSFixedWarning)
        configs_dir = os.path.join("photometrics", "configs")
        reference_dir = os.path.join(settings.DATA_ROOT, "reference_library")
        if os.path.exists(reference_dir) is False:
            os.makedirs(reference_dir)

        # Ensure paths end in slashes
        sci_dir = os.path.join(options['datadir'], '')
        dest_dir = os.path.join(options['datadir'], '')

        now = datetime.utcnow()
        now_string = now.strftime('%Y-%m-%d %H:%M')
        proc_filters = options['filter'] or 'all'
        prefix_text = ''
        if options['execute'] is False:
            prefix_text = '(dry-run) '
        self.stdout.write(f"==== Making {prefix_text}subtracted frames {now_string} ====")
        self.stdout.write(f"Block and filters to run for: Block Request# {options['blocknum']} filters: {proc_filters}")

        ### Find block corresponding to passed request number
        obs_blocks = Block.objects.filter(request_number=options['blocknum'], num_observed__gte=1)
        if obs_blocks.count() != 1:
            self.stdout.write(f"Observed Block with Request Number {options['blocknum']} not found")
            sys.exit(-1)
        obs_block = obs_blocks[0]

        # Verify directory and Block dayobs roughly match
        block_dayobs = obs_block.get_blockdayobs
        if block_dayobs not in sci_dir:
            self.stdout.write(f"Warning: Date of observation ({block_dayobs}) not found in path {sci_dir}")
        frames = Frame.objects.filter(block=obs_block, frametype=Frame.NEOX_RED_FRAMETYPE).order_by('midpoint')
        # List of the filters used on these frames
        obs_filters = frames.order_by('filter').values_list("filter", flat=True).distinct()
        filter_string = ",".join(obs_filters)
        if proc_filters != 'all':
            if proc_filters in obs_filters:
                obs_filters = [proc_filters, ]
            else:
                self.stdout.write(f"Requested filter {proc_filters} not observed in the Block (block filters: {filter_string})")
                sys.exit(-2)

        # Print out Block info and the frames we are combining
        filter_string = ",".join(obs_filters)
        num_frames = frames.count()

        field = determine_reffield_for_block(obs_block)

        if field is None:
            self.stdout.write(f"Reference field not found for {obs_block}")
            sys.exit(-1)

        self.stdout.write(f"\nMaking subtractions for: {field.current_name()} Block ID: {obs_block.id} ReqNum: {obs_block.request_number} Site: {obs_block.site}\n" \
                          f"Filter(s): {filter_string} Frames: {frames.earliest('midpoint')} -> {frames.latest('midpoint')} #Frames for Block: {num_frames}")

        ### Combine frames by filter type
        for obs_filter in obs_filters:
            filtered_frames = frames.filter(filter=obs_filter)

            # Print out filter info and the range of frames we are combining
            frame_nums = [int(f[23:27]) for f in filtered_frames.values_list("filename", flat=True)]
            filename = filtered_frames.values_list("filename", flat=True)[0]
            frame_prefix = filename[0:23]
            frame_suffix = filename[27:]
            out = []
            for _, g in groupby(enumerate(frame_nums), lambda k: k[0] - k[1]):
                start = next(g)[1]
                end = list(v for _, v in g) or [start]
                out.append(f'{frame_prefix}{start:04d} -- {end[-1]:04d}{frame_suffix}')
            filenames = ", ".join(out)

            msg = f"\nFilter: {obs_filter:>2s} Frames: {filenames} #Frames for filter: {filtered_frames.count()}"
            self.stdout.write(msg)

            ref_framepath = determine_reference_frame_for_block(obs_block, reference_dir, obs_filter)
            if ref_framepath:
                ref = ref_framepath
                self.stdout.write(f"Found reference frame {os.path.basename(ref)} in {os.path.dirname(ref)}")
                ## Symlink reference and rms frames
                frame = filtered_frames[0]
                dest_ref_name = os.path.join(dest_dir, f'reference_{obs_block.site}_{frame.instrument}_{obs_filter}.fits')
                if os.path.exists(dest_ref_name):
                    os.remove(dest_ref_name)
                os.symlink(ref, dest_ref_name)

                dest_ref_rms_name = dest_ref_name.replace('.fits', '.rms.fits')
                if os.path.exists(dest_ref_rms_name):
                    os.remove(dest_ref_rms_name)
                os.symlink(ref.replace('.fits', '.rms.fits'), dest_ref_rms_name)

                ## Find and process science frames
                sci_files = sorted(glob(sci_dir + f'{frame.filename[0:14]}*e92.fits'))
                self.stdout.write(f"Found {len(sci_files)} e92 frames with correct rootname in {sci_dir}, processing using {os.path.basename(dest_ref_name)}")
                start = time.time()
                if options['execute']:
                    status = run_hotpants_subtraction(dest_ref_name, sci_dir, configs_dir, dest_dir, sci_files)
                else:
                    self.stdout.write("SIM: Would run: run_hotpants_subtraction(dest_ref_name, sci_dir, configs_dir, dest_dir, sci_files)")
                end = time.time()
                self.stdout.write(f"subtraction took {end-start:.1f} seconds for {len(sci_files)} frames")

