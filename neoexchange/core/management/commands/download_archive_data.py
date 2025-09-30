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

import os
from sys import argv
from datetime import datetime, timedelta
from tempfile import mkdtemp, gettempdir
import shutil
from glob import glob

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage

from core.archive_subs import archive_login, get_frame_data, get_catalog_data, \
    determine_archive_start_end, download_files, make_data_dir, check_for_archive_images
from core.views import determine_active_proposals
from core.models import DataProduct, Block
from photometrics.gf_movie import make_movie
from photometrics.catalog_subs import sanitize_object_name
from core.utils import save_to_default, search, save_dataproduct


class Command(BaseCommand):

    help = 'Download data from the LCO Archive'

    def add_arguments(self, parser):
        if not settings.USE_S3:
            out_path = settings.DATA_ROOT
        else:
            out_path = mkdtemp()
        parser.add_argument('--date', action="store", default=None, help='Date of the data to download (YYYYMMDD)')
        parser.add_argument('--proposal', action="store", default=None, help="Proposal code to query for data (e.g. LCO2019B-023; default is for all active proposals)")
        parser.add_argument('--datadir', default=out_path, help='Place to save data (e.g. %s)' % out_path)
        parser.add_argument('--spectraonly', default=False, action='store_true', help='Whether to only download spectra')
        parser.add_argument('--dlengimaging', default=False, action='store_true', help='Whether to download imaging for LCOEngineering')
        parser.add_argument('--numdays', action="store", default=0.0, type=float, help='How many extra days to look for')

    def handle(self, *args, **options):
        usage = "Incorrect usage. Usage: %s [YYYYMMDD] [proposal code]" % ( argv[1] )

        if isinstance(options['date'], str):
            try:
                obs_date = datetime.strptime(options['date'], '%Y%m%d')
                obs_date += timedelta(seconds=17*3600)
            except ValueError:
                raise CommandError(usage)
        else:
            obs_date = options['date']

        proposals = determine_active_proposals(options['proposal'])
        if len(proposals) == 0:
            raise CommandError("No valid proposals found")

        verbose = True
        if options['verbosity'] < 1:
            verbose = False

        archive_token = settings.ARCHIVE_TOKEN
        if archive_token is not None:
            auth_headers = archive_login()
            start_date, end_date = determine_archive_start_end(obs_date)
            end_date = end_date + timedelta(days=options['numdays'])
            for proposal in proposals:
                self.stdout.write("Looking for frames between %s->%s from %s" % ( start_date, end_date, proposal ))
                obstypes = ['EXPOSE', 'ARC', 'LAMPFLAT', 'SPECTRUM']
                if (proposal == 'LCOEngineering' and options['dlengimaging'] is False) or options['spectraonly'] is True:
                    # Not interested in imaging frames
                    obstypes = ['ARC', 'LAMPFLAT', 'SPECTRUM']
                all_frames = {}
                for obstype in obstypes:
                    if obstype == 'EXPOSE':
                        redlevel = ['91', ]
                    else:
                        # '' seems to be needed to get the tarball of FLOYDS products
                        redlevel = ['0', '']
                    frames = get_frame_data(start_date, end_date, auth_headers, obstype, proposal, red_lvls=redlevel)
                    for red_lvl in frames.keys():
                        if red_lvl in all_frames:
                            all_frames[red_lvl] = all_frames[red_lvl] + frames[red_lvl]
                        else:
                            all_frames[red_lvl] = frames[red_lvl]
                    if 'CATALOG' in obstype or obstype == '':
                        catalogs = get_catalog_data(frames, auth_headers)
                        for red_lvl in frames.keys():
                            if red_lvl in all_frames:
                                all_frames[red_lvl] = all_frames[red_lvl] + catalogs[red_lvl]
                            else:
                                all_frames[red_lvl] = catalogs[red_lvl]
                for red_lvl in all_frames.keys():
                    self.stdout.write("Found %d frames for reduction level: %s" % (len(all_frames[red_lvl]), red_lvl))
                out_path = options['datadir']
                dl_frames = download_files(all_frames, out_path, verbose)
                self.stdout.write("Downloaded %d frames" % (len(dl_frames)))

                # unpack tarballs and make movie.
                for frame in all_frames.get('', []):
                    if "tar.gz" in frame['filename']:
                        tar_path = make_data_dir(out_path, frame)
                        obj = sanitize_object_name(frame['OBJECT'])
                        req_num = str(frame['REQNUM'])
                        movie_file = make_movie(frame['DATE_OBS'], obj, req_num, tar_path, out_path, frame['PROPID'], tarfile=frame['filename'])
                        blocks = Block.objects.filter(request_number=req_num)
                        for block in blocks:
                            if block.current_name() == frame['OBJECT']:
                                save_dataproduct(obj=block, filepath=movie_file, filetype=DataProduct.GUIDER_GIF)
                                filenames = glob(os.path.join(tar_path, obj + '_' + req_num, '*_2df_ex.fits'))
                                if filenames:
                                    for filename in filenames:
                                        save_dataproduct(obj=block, filepath=filename, filetype=DataProduct.FITS_SPECTRA)
                                break
                    elif "e91-1d" in frame['filename']:
                        tar_path = make_data_dir(out_path, frame)
                        obj = sanitize_object_name(frame['OBJECT'])
                        req_num = str(frame['REQNUM'])
                        # Fetch guide frames

                        guide_frames, num_total_frames = check_for_archive_images(req_num, obstype='GUIDE')
                        if num_total_frames > 0:
                            dl_frames = download_files({'0' : guide_frames}, out_path, verbose)
                            self.stdout.write("Downloaded %d guide frames" % (len(dl_frames)))
                            # Symlink guide frames into where make_movie() would expect them to be
                            # (We don't move them otherwise they will get redownloaded the next time this
                            # this script runs...) We know also need to check whether the object name
                            # in the entries in `guide_frames` from `check_for_archive_images` match
                            # as that will download all guider frames for the Request for both the target
                            # and spectral standard.
                            guide_path = os.path.join(tar_path, obj + '_' + req_num, 'Guide_frames')
                            if not os.path.exists(guide_path):
                                try:
                                    oldumask = os.umask(0o002)
                                    os.makedirs(guide_path)
                                    os.umask(oldumask)
                                except OSError:
                                    msg = "Error creating output path %s" % guide_path
                                    raise CommandError(msg)
                            os.makedirs(guide_path, exist_ok=True)
                            for guide_frame in guide_frames:
                                guide_framepath = os.path.join(tar_path, guide_frame['filename'])
                                dest_filepath = os.path.join(guide_path, guide_frame['filename'])
                                guide_obj = sanitize_object_name(guide_frame['target_name'])
                                if os.path.exists(dest_filepath) is False and guide_obj == obj:
                                    os.symlink(guide_framepath, dest_filepath)
                            movie_file = make_movie(frame['DATE_OBS'], obj, req_num, tar_path, tar_path, frame['PROPID'], tarfile=None)
                        blocks = Block.objects.filter(request_number=req_num)
                        for block in blocks:
                            if block.current_name() == frame['OBJECT']:
                                save_dataproduct(obj=block, filepath=movie_file, filetype=DataProduct.GUIDER_GIF)
                                filename = os.path.join(tar_path, frame['filename'])
                                save_dataproduct(obj=block, filepath=filename, filetype=DataProduct.FITS_SPECTRA)
                                break
            self.stdout.write("Done")
        else:
            self.stdout.write("No token defined (set ARCHIVE_TOKEN environment variable)")

        # Check if we're using a temp dir and then delete it
        if gettempdir() in out_path:
            shutil.rmtree(out_path)
