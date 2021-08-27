"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2016-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from urllib.parse import urljoin
import os
from datetime import datetime

from django.core.management.base import BaseCommand
from django.conf import settings

from core.models import Block, SuperBlock, Body, DataProduct, Frame
from core.views import find_spec
from core.utils import search, save_dataproduct
from core.archive_subs import lco_api_call
from photometrics.catalog_subs import sanitize_object_name


class Command(BaseCommand):

    help = 'Create DataProducts for already existing files.'

    def add_arguments(self, parser):
        parser.add_argument('--start', action="store", default='1900', help='Earliest Year to search (YYYY)')
        parser.add_argument('--overwrite', action="store_true", default=False,
                            help='Force overwrite and store robust data products')

    def handle(self, *args, **options):
        start_year = datetime.strptime(options['start'], '%Y')
        blocks = Block.objects.filter(num_observed__gte=1).filter(block_start__gte=start_year)
        n = 0
        a = 0
        s = 0
        tn_list = []
        for bl in blocks:
            obj_list = list({sanitize_object_name(bl.current_name()), bl.current_name().replace(' ', '_')})
            req = bl.request_number
            tn = bl.superblock.tracking_number
            date_obs_options = [str(int(bl.when_observed.strftime('%Y%m%d'))-0), str(int(bl.when_observed.strftime('%Y%m%d'))-1)]
            # find gifs
            for date_obs in date_obs_options:
                for obj in obj_list:
                    try:
                        path = os.path.join(date_obs, obj + '_' + req)
                    except TypeError:
                        continue
                    base_dir = date_obs
                    if bl.obstype in [Block.OPT_IMAGING, Block.OPT_IMAGING_CALIB]:
                        movie_file = "{}_{}_framemovie.gif".format(obj, req)
                    elif bl.obstype in [Block.OPT_SPECTRA, Block.OPT_SPECTRA_CALIB]:
                        movie_file = "{}_{}_guidemovie.gif".format(obj, req)
                        base_dir = os.path.join(path, "Guide_frames")
                    else:
                        movie_file = None
                    if movie_file:
                        gif_path = search(base_dir, movie_file, latest=True)
                        if gif_path:
                            n += 1
                            self.stdout.write(f"Found GIF for {bl.current_name()} in Block {bl.id} (Reqnum:{req}). \n"
                                              f"===> Creating DataProduct for {gif_path}.")
                            save_dataproduct(obj=bl, filepath=gif_path, filetype=DataProduct.FRAME_GIF, force=options['overwrite'])
                    spec_list = search(path, matchpattern='.*_2df_ex.fits', latest=False)
                    if spec_list:
                        for spec in spec_list:
                            s += 1
                            spec_path = os.path.join(path, spec)
                            self.stdout.write(f"Found Spectrum for {bl.current_name()} in Block {bl.id} (Reqnum:{req}). \n"
                                              f"===> Creating DataProduct for {spec_path}.")
                            save_dataproduct(obj=bl, filepath=spec_path, filetype=DataProduct.FITS_SPECTRA, force=options['overwrite'])
            # find ALCDEFs
            if tn not in tn_list:
                tn_list.append(tn)
                for obj in obj_list:
                    reduction_dir = os.path.join('Reduction', obj)
                    alcdef_base = f'.*.{tn}_ALCDEF.txt'
                    alcdef_list = search(reduction_dir, alcdef_base, latest=False)
                    if alcdef_list:
                        a += len(alcdef_list)
                        for alcfile in alcdef_list:
                            alc_path = os.path.join(reduction_dir, alcfile)
                            self.stdout.write(f"Found ALCDEF for {bl.current_name()} in SuperBlock {bl.superblock.id} (TrackingNum:{tn}). \n"
                                              f"===> Creating DataProduct for {alc_path}.")
                            save_dataproduct(obj=bl.superblock, filepath=alc_path, filetype=DataProduct.ALCDEF_TXT, force=options['overwrite'])
        self.stdout.write(f"{n} Gifs, {s} Spectra, and {a} ALCDEF Data products Created")

