import os
import numpy as np
from django.core.management.base import BaseCommand, CommandError
from core.models import SuperBlock, Block, Body,Frame
from astropy.table import Table
#from astropy.Time import now

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('-t','--total_time',type=float, default=0.0, help='Minimum total exposure time (m) of block')
        #parser.add_argument('-s','--start',type=float,default=0, help='Starting time (JD) of included observations')
        #parser.add_argument('-e','--end',type=float,default=Time.now().jd, help='Ending time (JD) of included observations')
        parser.add_argument('-b','--body',type=str, default=None, help='Find observations of specific object only')
        parser.add_argument('-o','--obs',type=str,default=None, help='Find specific observation based on tracking number')

    def handle(self, *args, **options):

        if options['body']:
            blocks = list(SuperBlock.objects.filter(body=Body.objects.filter(name=options['body'])))
        # elif options['start']:
        #     if options['body']:
        #         blocks = list(SuperBlock.objects.filter(body=Body.objects.filter(name=options['body'], block_start__gte=datetime(options['start']))))
        #     else:
        #         blocks = list(SuperBlock.objects.filter(body=Body.objects.filter(block_start__gte=datetime(options['start']))))
        else:
            if options['obs']:
                blocks = list(SuperBlock.objects.filter(tracking_number=options['obs']))
            else:
                blocks = list(SuperBlock.objects.all())

        long_obs = np.array([])
        tab = Table(names=('Superblock ID', 'Group ID', 'Object', 'total subblocks', 'red frames', 'good frames', 'exposure time (m)'),
        dtype= ('S','S','S','i4','i4','i4','f4'))
#FIGURE OUT TIMING LOGIC LATER
        for block in blocks:
            num_exps = list(Block.objects.filter(superblock=block.id).values_list('num_exposures'))
            len_exps = list(Block.objects.filter(superblock=block.id).values_list('exp_length'))
            obs = block.get_num_observed()[0]
            redframes = 0
            goodframes = 0
            if obs:
                for subblock in list(Block.objects.filter(superblock=block.id)):
                    redframe = subblock.num_unique_red_frames()
                    goodframe = Frame.objects.filter(block=subblock.id,frametype__in=[Frame.BANZAI_RED_FRAMETYPE],zeropoint__isnull=False,zeropoint__gt=-99).count()
                    redframes += redframe
                    goodframes += goodframe
                    #frames = np.append(frames, list(Frame.objects.filter(block=subblock.id)))
                #if redframe:
                    #print('Superblock ID: %s\nSubblock ID: %s\nredframes: %i\ngood frames: %i\n' % (block.id,subblock.id,redframe,goodframe))
                #goodframes = Frame.objects.filter(block=block.id,zeropoint__isnull=False,zeropoint__gt=-99).count()
                #goodframes = Frame.objects.filter(block=block.id, zeropoint__isnull=False, frametype__in=[Frame.BANZAI_QL_FRAMETYPE]).count()

                #len_exps = list(Frame.objects.filter(block=list(Block.objects.filter(superblock=block.id))[0]))[0].exptime
                #print('Block ID: %s\ntotal subblocks = %d\nredframes = %d\ngoodframes = %d\n' % (block.tracking_number,len(num_exps),redframes,goodframes))
                #long_obs = np.append(long_obs,[redframes,len_exps[0][0],block.tracking_number,block.body.current_name()])
                #print('rf=',redframes,'et=',len_exps)

            # if len(frames):
            #     time = float(abs(frames[-1].midpoint-frames[0].midpoint).total_seconds()/3600)
            #     if time > .65:
            #         print('Elapsed time: %.3fh' % time)
            #         print('Block: %s\n' % block.tracking_number)

                total_exp = redframes*float(len_exps[0][0])/60
                if total_exp >= options['total_time']:
                    tab.add_row((block.tracking_number,block.groupid,block.body.current_name(),
                    len(num_exps),redframes,goodframes,round(total_exp,2)))
                    long_obs = np.append(long_obs, block)
                     #print('Block ID: %s\nGroup ID: %s\nObject: %s\ntotal subblocks= %d\nreduced frames= %d\ngood zp frames= %d\nTime observed: %.3f m\n' %
                     #(block.id,block.groupid,block.body.current_name(),len(num_exps),redframes,goodframes,total_exp))

        tab.pprint(max_lines=-1)

        print('Total observations: %i' % len(long_obs))
