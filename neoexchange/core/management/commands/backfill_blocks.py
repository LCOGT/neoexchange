import os
from sys import argv
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from core.models import Frame, Block, SuperBlock, Body, Proposal
from photometrics.catalog_subs import get_fits_files, open_fits_catalog
from core.frames import block_status, create_frame

class Command(BaseCommand):

    help = 'Hacky command to create Body, Block, SuperBlock and Frames for downloaded data'

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
            if len(fits_files) == 0:
                continue
            first_file = fits_files[0]
            header, dummy_table, cattype = open_fits_catalog(first_file, header_only=True)
            tracking_num = header.get('tracknum', None)
            if tracking_num and tracking_num!='UNSPECIFIED':
                tracking_num_nopad = tracking_num.lstrip('0')
                sblocks = SuperBlock.objects.filter(Q(tracking_number=tracking_num)|Q(tracking_number=tracking_num_nopad))
                if len(sblocks) == 0:
                    name = header.get('object', None)
                    if name:
                        # Take out any parentheses e.g. (28484)
                        name = name.replace('(', '').replace(')', '')
                    bodies = Body.objects.filter(Q(provisional_name__exact = name )|Q(provisional_packed__exact = name)|Q(name__exact = name))
                    if len(bodies) == 1:
                        body = bodies[0]
                        sblock_params = { 'active': True,
                                          'block_start': header.get('blksdate'),
                                          'block_end'  : header.get('blkedate'),
                                          'body': body,
                                          'groupid'   : header.get('groupid', ''),
                                          'proposal' : Proposal.objects.get(code=header.get('propid', '')),
                                          'tracking_number': tracking_num,
                                        }
                        new_sblock = SuperBlock.objects.create(**sblock_params)
                        block_params = { 'superblock' : new_sblock,
                                         'active': True,
                                         'block_start': header.get('blksdate'),
                                         'block_end'  : header.get('blkedate'),
                                         'body': body,
                                         'exp_length': header.get('exptime'),
                                         'groupid'   : header.get('groupid', ''),
                                         'num_exposures': header.get('frmtotal', 0),
                                         'proposal' : Proposal.objects.get(code=header.get('propid', '')),
                                         'site'     : header.get('siteid'),
                                         'telclass' : header['telid'][0:3],
                                         'tracking_number': header.get('reqnum', tracking_num)
                                       }
                        new_block = Block.objects.create(**block_params)
                        self.stdout.write("Updating status of new Block %d" % new_block.id)
                        block_status(new_block.id)
                    else:
                        self.stdout.write("Could not find Body from FITS data (OBJECT=%s)" % name)
                elif len(sblocks) == 1:
                    old_sblock = sblocks[0]
                    blocks = Block.objects.filter(superblock=old_sblock)
                    if blocks.count() == 0:
                        msg = "Could not find any Blocks to match SuperBlock #%d (%s)" % (old_sblock.id, old_sblock.tracking_number)
                        self.stdout.write(msg)
                    else:
                        self.stdout.write("Checking sub Block status for SuperBlock #%d" % old_sblock.id)
                        for sub_block in blocks:
                            if sub_block.tracking_number == header.get('reqnum', tracking_num):
                                self.stdout.write("Found Block %d with matching REQNUM=%s" % (sub_block.id, sub_block.tracking_number))
                                frames = Frame.objects.filter(block=sub_block, frametype__in=(Frame.BANZAI_QL_FRAMETYPE, Frame.BANZAI_RED_FRAMETYPE))
                                if len(fits_files) >= frames.count():
                                    self.stdout.write("Updating status of Block #%d (found %d FITS files, know of %d Frames in DB)" % (sub_block.id,len(fits_files), frames.count()))
                                    block_status(sub_block.id)
                                else:
                                    self.stdout.write("Already have more/right number of frames for Block #%d (found %d FITS files, know of %d Frames in DB)" % (sub_block.id,len(fits_files), frames.count()))

                elif len(sblocks) >= 2:
                        msg = "Found multiple SuperBlocks "
                        msg += "%s" % ( [sblock.id for sblock in sblocks])
                        msg += " in DB for tracking number %s. Fix up manually" % tracking_num
                        self.stdout.write(msg)
            else:
                self.stdout.write("Could not obtain tracking number (did this bypass the scheduler!?)")
                #Fetch groupid from header; use to find Block; pass header and Block to create_frame
                for fits_file in fits_files:
                    header, dummy_table, cattype = open_fits_catalog(fits_file, header_only=True)
                    if header != {}:
                        header['DATE_OBS'] = header['DATE-OBS']
                        group_id = header.get('groupid', None)
                        block = Block.objects.get(groupid=group_id)
                        frame = create_frame(header, block)
                if header != {}:
                    block.when_observed = datetime.strptime(header['DATE-OBS'][:19],'%Y-%m-%dT%H:%M:%S')
                    block.num_observed = 1
                    block.save()
                else:
                    self.stdout.write("Could not find fits file!")
