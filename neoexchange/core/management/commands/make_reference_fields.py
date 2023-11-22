"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2022-2022 LCO

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
import tempfile
import shutil
from datetime import datetime

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from astropy.wcs import FITSFixedWarning

from core.models import StaticSource, Block, Frame
from core.views import run_swarp_make_reference, determine_images_and_catalogs
from photometrics.image_subs import get_reference_name, find_reference_images
from photometrics.catalog_subs import funpack_fits_file

class Command(BaseCommand):
    help = "Make a reference field"

    def add_arguments(self, parser):
        parser.add_argument('site', type=str, nargs='?', default=None, help='Site to run for. Default is all sites.')
        parser.add_argument('--datadir', action="store", default=None, help='Path for processed data (e.g. /data/eng/rocks)')
        parser.add_argument('--blocknum', type=int, default=None, help='Block (request number) to analyze')
        # Make an argument for specific blocks

    def handle(self, *args, **options):
        warnings.simplefilter("ignore", FITSFixedWarning)
        configs_dir = os.path.join("photometrics", "configs")

        ### Filtering fields by site name

        self.stdout.write(f"Sites to run for: {options['site']}")

        ref_fields = StaticSource.objects.filter(source_type=StaticSource.REFERENCE_FIELD)
        self.stdout.write(f"Number of reference fields before filtering: {ref_fields.count()}")
        if options['site'] is not None:
            site = options['site'].upper()
            ref_fields = ref_fields.filter(name__contains=site)

        self.stdout.write(f"Number of reference fields after filtering: {ref_fields.count()}\n")

        ### Loop over reference fields and make a list of the observed fields
        obs_fields=[]
        for field in ref_fields:
            blocks = Block.objects.filter(calibsource=field)
            obs_blocks = blocks.filter(num_observed__gte=1)
            if obs_blocks.count() > 0:
                obs_fields.append(field)

            # Print out relative info for each of the reference fields
            self.stdout.write(f"{field.name}: {field.ra: 9.5f} {field.dec:+9.5f}  Num blocks: {blocks.count()}  Num observed blocks: {obs_blocks.count()}")

        # Loop over all observed fields
        for field in obs_fields:
            ### Find blocks corresponding to observed fields
            obs_blocks = Block.objects.filter(calibsource=field, num_observed__gte=1)
            if options['blocknum'] is not None:
                obs_blocks = obs_blocks.filter(request_number=options['blocknum'])
            for obs_block in obs_blocks:
                # Find frames corresponding to each block
                frames = Frame.objects.filter(block=obs_block, frametype=Frame.BANZAI_RED_FRAMETYPE)
                # List of the filters used on these frames
                obs_filters = frames.values_list("filter", flat=True).distinct()

                # Print out Block info and the frames we are combining
                filter_string = ",".join(obs_filters)
                num_frames = frames.count()
                self.stdout.write(f"\nMaking reference field for: {field.name} Block ID: {obs_block.id} ReqNum: {obs_block.request_number} Site: {obs_block.site}\n" \
                                  f"Filter(s): {filter_string} Frames: {frames.earliest('midpoint')} -> {frames.latest('midpoint')} Num Frames: {num_frames}")

                ### Combine frames by filter type
                for obs_filter in obs_filters:
                    filtered_frames = frames.filter(filter=obs_filter)

                    # Print out filter info and the frames we are combining
                    filenames = ", ".join(filtered_frames.values_list("filename", flat=True))
                    msg = f"\nFilter: {obs_filter:>2s} Frames: {filenames} Num frames: {filtered_frames.count()}"
                    self.stdout.write(msg)

                    # Find all existing reference frames
                    reference_dir = os.path.join(settings.DATA_ROOT, "reference_library")
                    if os.path.exists(reference_dir) is False:
                        os.makedirs(reference_dir)
                    ref_frames = find_reference_images(reference_dir, "reference*.fits")

                    # Check if existing reference frame exists
                    # If not, make one
                    ref_frame_name = get_reference_name(field.ra, field.dec, obs_block.site, filtered_frames[0].instrument, obs_filter)
                    match_ref_frames = [frame for frame in ref_frames if os.path.basename(frame)==ref_frame_name]

                    if len(match_ref_frames) == 0:
                        self.stdout.write(f"Reference frame ({ref_frame_name}) not found in {reference_dir}")
                        if options['datadir'] is None:
                            dest_dir = tempfile.mkdtemp(prefix='tmp_neox_reffield_')
                        else:
                            dest_dir = options['datadir']
                        dest_dir = os.path.join(dest_dir, "")

                        # Check for processed frames already
                        images, catalogs = determine_images_and_catalogs(self, dest_dir, red_level='e92')
                        if images is not None:
                            images_filenames = [os.path.basename(f) for f in images]
                            red_frames = [x.replace('e91', 'e92') for x in filtered_frames.values_list('filename', flat=True)]
                            num_images = 0
                            for red_frame in red_frames:
                                if red_frame in images_filenames:
                                    num_images += 1
                        else:
                            num_images = 0
                        if catalogs is not None:
                            catalogs_filenames = [os.path.basename(f) for f in catalogs]
                            red_catalogs = [x.replace('e91', 'e92_ldac') for x in filtered_frames.values_list('filename', flat=True)]
                            num_catalogs = 0
                            for red_catalog in red_catalogs:
                                if red_catalog in catalogs_filenames:
                                    num_catalogs += 1
                        else:
                            num_catalogs = 0
                        if images is None and catalogs is None or (num_images != filtered_frames.count() and num_catalogs != filtered_frames.count()):
                            self.stdout.write(f"Not all products present, running frame reduction pipeline in {dest_dir}")

                            year = filtered_frames[0].midpoint.year
                            if year == datetime.utcnow().year:
                                year = ""
                            day_obs = filtered_frames[0].filename.split("-")[2]
                            source_dir = os.path.join(settings.DATA_ROOT, str(year), day_obs)

                            # Copy each frame to a temporary directory
                            for frame_filename in filtered_frames.values_list("filename", flat=True):
                                fz_frame = frame_filename.replace(".fits", ".fits.fz")
                                fz_frame_copied = os.path.join(dest_dir, fz_frame)
                                if os.path.exists(fz_frame_copied) is False:
                                    shutil.copy(os.path.join(source_dir, fz_frame), dest_dir)
                                    funpack_fits_file(fz_frame_copied, all_hdus=True)

                            # Run frame reduction pipeline
                            call_command('run_pipeline', '--datadir', dest_dir, '--tempdir', dest_dir, '--refcat', 'PS1')

                        # SWarp the frames, and output to the temporary directory
                        run_swarp_make_reference(dest_dir, configs_dir, dest_dir, match="*e92.fits")

                        #Copy the finished reference image and rms image to the reference library.
                        if os.path.exists(os.path.join(dest_dir, "reference.fits")):
                            shutil.copy(os.path.join(dest_dir, "reference.fits"), os.path.join(reference_dir, ref_frame_name))
                        if os.path.exists(os.path.join(dest_dir, "reference.rms.fits")):
                            ref_rmsframe_name = ref_frame_name.replace('.fits', '.rms.fits')
                            shutil.copy(os.path.join(dest_dir, "reference.rms.fits"), os.path.join(reference_dir, ref_rmsframe_name))
                    else:
                        self.stdout.write(f"Reference frame {ref_frame_name} already exists.")

                self.stdout.write("")
            self.stdout.write("")


