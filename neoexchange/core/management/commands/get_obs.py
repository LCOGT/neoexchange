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

    Prints a list of successful observations that fit the given arguments.
    Included in list is information about group, object, time, frames, exposure time
"""

import os
import numpy as np
from django.core.management.base import BaseCommand, CommandError
from core.models import SuperBlock, Block, Body, Frame
from astropy.table import Table


class Command(BaseCommand):

    help = 'Prints a table of successful observation blocks in the DB that fit the given arguments. If given no arguments, this will fail.'

    def add_arguments(self, parser):
        parser.add_argument('-t', '--total_time', type=float, default=0.0, help='Minimum total exposure time (m) of block')
        # parser.add_argument('-s','--start',type=float,default=0, help='Starting time (JD) of included observations')
        # parser.add_argument('-e','--end',type=float,default=Time.now().jd, help='Ending time (JD) of included observations')
        parser.add_argument('-b', '--body', type=str, default=None, help='Find observations of specific object only. (If object name has spaces, put in quotes.)')
        parser.add_argument('-o', '--obs', type=str, default=None, help='Find specific observation based on tracking number.')

    def handle(self, *args, **options):
        # initial filtering
        if options['body']:
            blocks = SuperBlock.objects.filter(body=Body.objects.filter(name=options['body']))
        else:
            if options['obs']:
                blocks = SuperBlock.objects.filter(tracking_number=options['obs'])
            else:
                msg = "No input arguments. Either use -b 'Object Name' or -o trackingnumber "
                raise CommandError(msg)
        long_obs = np.array([])
        tab = Table(names=('Superblock ID', 'Group ID', 'Object', 'total subblocks', 'red frames', 'good frames',
                           'exposure time (m)'), dtype=('S', 'S', 'S', 'i4', 'i4', 'i4', 'f4'))
        # finding number of frames and their type (total, reduced, good zp)
        for block in blocks:
            num_exps = Block.objects.filter(superblock=block.id).values_list('num_exposures')
            len_exps = Block.objects.filter(superblock=block.id).values_list('exp_length')
            obs = block.get_num_observed()[0]
            redframes = 0
            goodframes = 0
            if obs:
                for subblock in Block.objects.filter(superblock=block.id):
                    redframe = subblock.num_unique_red_frames()
                    goodframe = Frame.objects.filter(block=subblock.id, frametype__in=[Frame.BANZAI_RED_FRAMETYPE], zeropoint__isnull=False, zeropoint__gt=-99).count()
                    redframes += redframe
                    goodframes += goodframe
                # calculating exposure time
                total_exp = redframes*float(len_exps[0][0])/60
                if total_exp >= options['total_time']:
                    tab.add_row((block.tracking_number, block.groupid, block.body.current_name(),
                    len(num_exps), redframes, goodframes, round(total_exp, 2)))
                    long_obs = np.append(long_obs, block)

        tab.pprint(max_lines=-1)

        print('Total observations: %i' % len(long_obs))
