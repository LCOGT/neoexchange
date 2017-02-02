import os
from sys import argv
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from core.models import Frame, Block, Body, Proposal
from photometrics.catalog_subs import get_fits_files, open_fits_catalog
from core.frames import block_status

class Command(BaseCommand):

    help = 'Download and pipeline process data from the LCO Archive'

    def add_arguments(self, parser):
        default_path = os.path.join(os.path.sep, 'data', 'eng', 'rocks')
        parser.add_argument('--date', action="store", default=datetime.utcnow(), help='Date of the data to download (YYYYMMDD)')
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
        dataroot = options['datadir']

        if not os.path.exists(dataroot):
            msg = "Error reading output path %s" % dataroot
            raise CommandError(msg)

        # Append date to the data directory
        dataroot = os.path.join(dataroot, obs_date)

        object_dirs = [x[0] for x in os.walk(dataroot)]

        for rock in object_dirs[1:]:
            datadir = os.path.join(dataroot, rock)
            self.stdout.write('Processing target %s in %s' % (rock, datadir))
            fits_files = get_fits_files(datadir)
            self.stdout.write("Found %d FITS files in %s" % (len(fits_files), datadir) )
            first_file = fits_files[0]
            header, dummy_table, cattype = open_fits_catalog(first_file, header_only=True)
            tracking_num = header.get('tracknum', None)
            if tracking_num:
                blocks = Block.objects.filter(tracking_number=tracking_num)
                if len(blocks) == 0:
                    name = header.get('object', None)
                    bodies = Body.objects.filter(Q(provisional_name__exact = name )|Q(provisional_packed__exact = name)|Q(name__exact = name))
                    if len(bodies) == 1:
                        body = bodies[0]
                        block_params = { 'active': True,
                                         'block_start': header.get('blksdate'),
                                         'block_end'  : header.get('blkedate'),
                                         'body': body,
                                         'exp_length': header.get('exptime'),
                                         'groupid'   : header.get('groupid', ''),
                                         'num_exposures': header.get('frmtotal', 0),
                                         'proposal' : Proposal.objects.get(code=header.get('propid', '')),
                                         'site'     : header.get('siteid'),
                                         'telclass' : header['telid'][0:3],
                                         'tracking_number': tracking_num,
                                       }
                        new_block = Block.objects.create(**block_params)
                        block_status(new_block.id)
                    else:
                        self.stdout.write("Could not find Body from FITS data (OBJECT=%s)" % name)
            else:
                self.stdout.write("Could not obtain tracking number (did this bypass the scheduler!?")
