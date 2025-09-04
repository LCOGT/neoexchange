"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2017-2019 LCO

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
import pprint
from sys import argv, exit
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from core.models import Frame, Block, SuperBlock, Body, Proposal
from photometrics.catalog_subs import get_fits_files, open_fits_catalog, get_catalog_header
from core.frames import block_status, create_frame

class Command(BaseCommand):

    help = 'Hacky command to create Body, Block, SuperBlock and Frames for downloaded data'

    def add_arguments(self, parser):
        default_path = os.path.join(os.path.sep, 'data', 'eng', 'rocks')
        default_pattern = '*e91.fits'
        parser.add_argument('--date', action="store", default=datetime.utcnow(), help='Date of the data to download (YYYYMMDD)')
        parser.add_argument('--datadir', action="store", default=default_path, help='Path for processed data (e.g. /data/eng/rocks)')
        parser.add_argument('--fitspattern', action="store", default=default_pattern, help=f'Match pattern for FITS files (default: {default_pattern})')

    def handle(self, *args, **options):
        usage = "Incorrect usage. Usage: %s --date [YYYYMMDD] --datadir [path] --fitspattern [pattern]" % ( argv[1] )


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

        #object_dirs = [x[0] for x in os.walk(dataroot) if ('Didymos' in x[0] or '65803' in x[0] or obs_date in x[0][-8:]) and 'Temp_cvc' not in x[0]]
        #object_dirs = [x[0] for x in os.walk(dataroot) if ('3I' in x[0] or 'C_2025N1' in x[0] or 'c_2025n1' in x[0] or obs_date in x[0][-8:]) and 'Temp_cvc' not in x[0]]
        object_dirs = [x[0] for x in os.walk(dataroot) if ('P_2016P5' in x[0] or obs_date in x[0][-8:]) and 'Temp_cvc' not in x[0]]

        pprint.pprint(object_dirs)
        for rock in object_dirs[1:]:
            datadir = os.path.join(dataroot, rock)
            self.stdout.write('Processing target %s in %s looking for %s' % (rock, datadir, options['fitspattern']))
            fits_files = get_fits_files(datadir, options['fitspattern'])
            self.stdout.write("Found %d FITS files in %s" % (len(fits_files), datadir) )
            if len(fits_files) < 1:
                self.stdout.write('Too few FITS files found, skipping')
                continue
            first_file = fits_files[0]
            fits_header, dummy_table, cattype = open_fits_catalog(first_file, header_only=True)
            header = get_catalog_header(fits_header, cattype)
            tracking_num = header.get('tracking_number', None)
            if tracking_num and tracking_num!='UNSPECIFIED':
                tracking_num_nopad = tracking_num.lstrip('0')
                sblocks = SuperBlock.objects.filter(Q(tracking_number=tracking_num)|Q(tracking_number=tracking_num_nopad))
                if sblocks.count() == 0:
                    name = header.get('object_name', None)
                    if name:
                        # Take out any parentheses e.g. (28484)
                        name = name.rstrip().replace('(', '').replace(')', '')
                        # Account for the many variations on a theme...
                        #name.replace('Didymos', '65803')
                        name = name.replace('C/2025 N1', '3I').replace('c/2025 n1', '3I').replace('c/2025n1', '3I').replace('3IATLAS', '3I').replace('C/2025N1', '3I')
                        # MRO-specific oddities
                        if header.get('site_id', '') == 'MRO':
                            name = name.replace('R', '').replace('V', '').replace('didcomps', 'didymos').replace('comps', 'mos').replace('compc', 'mos').replace('comp', 'mos')
                            name = name.replace('didymos', '65803')
                    bodies = Body.objects.filter(Q(provisional_name__exact = name )|Q(provisional_packed__exact = name)|Q(name__exact = name))
                    if bodies.count() == 1:
                        body = bodies[0]
                        try:
                            proposal_object = Proposal.objects.get(code=header.get('proposal', ''))
                        except Proposal.DoesNotExist:
                            self.stdout.write(f"Couldn't find Proposal with code={header.get('proposal', '')}")
                            raise
                        sblock_params = { 'active': True,
                                          'block_start': header.get('block_start'),
                                          'block_end'  : header.get('block_end'),
                                          'body': body,
                                          'groupid'   : header.get('groupid', ''),
                                          'proposal' : proposal_object,
                                          'tracking_number': tracking_num,
                                        }
                        new_sblock, created = SuperBlock.objects.get_or_create(**sblock_params)
                        #created = True
                        print(f"SuperBlock created ? {created}")
                        if created:
                            pprint.pprint(sblock_params, indent=4)
                        block_params = { 'superblock' : new_sblock,
                                         'block_start': header.get('block_start'),
                                         'block_end'  : header.get('block_end'),
                                         'body': body,
                                         'exp_length': header.get('exptime'),
                                         'num_exposures': header.get('num_exposures', 0),
                                         'site'     : header.get('site_id'),
                                         'telclass' : header['tel_id'][0:3],
                                         'request_number': header.get('request_number', tracking_num),
                                         'tracking_rate' : int(header.get('tracfrac', 1.0)*100)
                                       }
                        new_block, created = Block.objects.get_or_create(**block_params)
                        new_block.active = True
                        new_block.save()
                        print(f"Block created ? {created}")
                        if created:
                            pprint.pprint(block_params, indent=4)
                        self.stdout.write("Updating status of new Block %d" % new_block.id)
                        block_status(new_block.id, datadir)
                    else:
                        self.stdout.write("Could not find Body from FITS data (OBJECT=%s)" % name)
                elif sblocks.count() == 1:
                    old_sblock = sblocks[0]
                    blocks = Block.objects.filter(superblock=old_sblock)
                    if blocks.count() == 0:
                        msg = "Could not find any Blocks to match SuperBlock #%d (%s)" % (old_sblock.id, old_sblock.tracking_number)
                        self.stdout.write(msg)
                    else:
                        self.stdout.write("Checking sub Block status for SuperBlock #%d" % old_sblock.id)
                        existing_requests = blocks.values_list('request_number', flat=True).distinct()
                        request_num = header.get('request_number', '')
                        if request_num in existing_requests:
                            sub_block = blocks.get(request_number=request_num)
                            self.stdout.write("Found Block %d with matching REQNUM=%s" % (sub_block.id, sub_block.request_number))
                            frames = Frame.objects.filter(block=sub_block, frametype__in=(Frame.BANZAI_RED_FRAMETYPE, Frame.SWOPE_RED_FRAMETYPE, Frame.MRO_RED_FRAMETYPE))
                            if len(fits_files) > frames.count():
                                self.stdout.write("Updating status of Block #%d (found %d FITS files, know of %d Frames in DB)" % (sub_block.id,len(fits_files), frames.count()))
                                block_status(sub_block.id, datadir)
                            else:
                                self.stdout.write("Already have more/right number of frames for Block #%d (found %d FITS files, know of %d Frames in DB)" % (sub_block.id,len(fits_files), frames.count()))
                        else:
                            self.stdout.write("New Block with REQNUM=%s needed for SuperBlock #%d" % (request_num, old_sblock.id))
                            block_params = { 'superblock' : old_sblock,
                                     'active' : True,
                                     'block_start': header.get('block_start'),
                                     'block_end'  : header.get('block_end'),
                                     'body': old_sblock.body,
                                     'exp_length': header.get('exptime'),
                                     'num_exposures': header.get('num_exposures', 0),
                                     'site'     : header.get('site_id'),
                                     'telclass' : header['tel_id'][0:3],
                                     'request_number': header.get('request_number', ''),
                                     'tracking_rate' : int(header.get('tracrate_frac', 1.0)*100)
                                   }
                            new_block, created = Block.objects.get_or_create(**block_params)
                            print(f"Block created ? {created}")
                            if created:
                                pprint.pprint(new_block, indent=4)
                            self.stdout.write("Updating status of new Block %d" % new_block.id)
                            block_status(new_block.id)
                elif sblocks.count() >= 2:
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
