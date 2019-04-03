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

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from core.archive_subs import archive_login, get_frame_data, get_catalog_data, \
    determine_archive_start_end, download_files
from core.views import make_movie, make_spec, determine_active_proposals


class Command(BaseCommand):

    help = 'Download data from the LCO Archive'

    def add_arguments(self, parser):
        out_path = settings.DATA_ROOT
        parser.add_argument('--date', action="store", default=datetime.utcnow(), help='Date of the data to download (YYYYMMDD)')
        parser.add_argument('--proposal', action="store", default=None, help="Proposal code to query for data (e.g. LCO2019A-006; default is for all active proposals)")
        parser.add_argument('--datadir', default=out_path, help='Place to save data (e.g. %s)' % out_path)
        parser.add_argument('--spectraonly', default=False, action='store_true', help='Whether to only download spectra')

    def handle(self, *args, **options):
        usage = "Incorrect usage. Usage: %s [YYYYMMDD] [proposal code]" % ( argv[1] )

        if type(options['date']) != datetime:
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

        username = os.environ.get('NEOX_ODIN_USER', None)
        password = os.environ.get('NEOX_ODIN_PASSWD', None)
        archive_token = os.environ.get('ARCHIVE_TOKEN', None)
        if (username is not None and password is not None) or archive_token is not None:
            auth_headers = archive_login(username, password)
            start_date, end_date = determine_archive_start_end(obs_date)
            for proposal in proposals:
                self.stdout.write("Looking for frames between %s->%s from %s" % ( start_date, end_date, proposal ))
                obstypes = ['EXPOSE', 'ARC', 'LAMPFLAT', 'SPECTRUM']
                if proposal == 'LCOEngineering' or options['spectraonly'] is True:
                    # Not interested in imaging frames
                    obstypes = ['ARC', 'LAMPFLAT', 'SPECTRUM']
                all_frames = {}
                for obstype in obstypes:
                    if obstype == 'EXPOSE':
                        redlevel = ['91', '11']
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
                    self.stdout.write("Found %d frames for reduction level: %s" % ( len(all_frames[red_lvl]), red_lvl ))
                daydir = start_date.strftime('%Y%m%d')
                out_path = os.path.join(options['datadir'], daydir)
                if not os.path.exists(out_path):
                    try:
                        os.makedirs(out_path)
                    except:
                        msg = "Error creating output path %s" % out_path
                        raise CommandError(msg)
                self.stdout.write("Downloading data to %s" % out_path)
                dl_frames = download_files(all_frames, out_path, verbose)
                self.stdout.write("Downloaded %d frames" % ( len(dl_frames) ))
                # unpack tarballs and make movie.
                for frame in all_frames['']:
                    if "tar.gz" in frame['filename']:
                        make_movie(obs_date, frame['OBJECT'].replace(" ", "_"), str(frame['REQNUM']), out_path, frame['PROPID'])
                        spec_plot, spec_count = make_spec(obs_date, frame['OBJECT'].replace(" ", "_"), str(frame['REQNUM']), out_path, frame['PROPID'], 1)
                        if spec_count > 1:
                            for obs in range(2, spec_count+1):
                                make_spec(obs_date, frame['OBJECT'].replace(" ", "_"), str(frame['REQNUM']), out_path, frame['PROPID'], obs)
        else:
            self.stdout.write("No username and password or token defined (set NEOX_ODIN_USER and NEOX_ODIN_PASSWD or ARCHIVE_TOKEN)")
