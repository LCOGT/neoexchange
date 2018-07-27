import os
from sys import argv
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from core.archive_subs import archive_login, get_frame_data, get_catalog_data, \
    determine_archive_start_end, download_files


class Command(BaseCommand):

    help = 'Download data from the LCO Archive'

    def add_arguments(self, parser):
        parser.add_argument('--date', action="store", default=datetime.utcnow(), help='Date of the data to download (YYYYMMDD)')
        parser.add_argument('--proposal', action="store", default="LCO2018B-013", help='Proposal code to query for data (e.g. LCO2018b-013)')
        out_path = os.path.join(os.environ.get('HOME'), 'Asteroids')
        parser.add_argument('--datadir', default=out_path, help='Place to save data (e.g. %s)' % out_path)

    def handle(self, *args, **options):
        usage = "Incorrect usage. Usage: %s [YYYYMMDD] [proposal code]" % ( argv[1] )
        obstypes = ['EXPOSE', 'ARC', 'LAMPFLAT', 'SPECTRUM']
        if options['proposal'] == 'LCOEngineering':
            # Not interested in imaging frames
            obstypes = ['ARC', 'LAMPFLAT', 'SPECTRUM']

        if type(options['date']) != datetime:
            try:
                obs_date = datetime.strptime(options['date'], '%Y%m%d')
                obs_date += timedelta(seconds=17*3600)
            except ValueError:
                raise CommandError(usage)
        else:
            obs_date = options['date']
        proposal = options['proposal']
        verbose = True
        if options['verbosity'] < 1:
            verbose = False

        username = os.environ.get('NEOX_ODIN_USER', None)
        password = os.environ.get('NEOX_ODIN_PASSWD',None)
        if username and password:
            auth_headers = archive_login(username, password)
            start_date, end_date = determine_archive_start_end(obs_date)
            self.stdout.write("Looking for frames between %s->%s from %s" % ( start_date, end_date, proposal ))
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
        else:
            self.stdout.write("No username or password defined (set NEOX_ODIN_USER and NEOX_ODIN_PASSWD)")
