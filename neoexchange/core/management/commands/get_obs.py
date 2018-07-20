import os
import numpy as np
from django.core.management.base import BaseCommand, CommandError
from core.models import SuperBlock, Block

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('total_time',type=float, default=0.0, help='Minimum total exposure time (s) of block')
        parser.add_argument('-s','--start',type=float,default=0, help='Starting time (JD) of included observations')
        parser.add_argument('-e','--end',type=float,default=0, help='Ending time (JD) of included observations')
        parser.add_argument('-b','--body',type=str, default=None, help='Find observations of specific object only')

    def handle(self, *args, **options):

        if not options['body']:
            blocks = list(SuperBlock.objects.all())
        else:
            blocks = list(SuperBlock.objects.filter(body=options['body']))

        long_obs = np.array([[]])
#FIGURE OUT TIMING LOGIC LATER
        for block in blocks:
            num_exps = list(Block.objects.filter(superblock=block.id).values_list('num_exposures'))
            len_exps = list(Block.objects.filter(superblock=block.id).values_list('exp_length'))
            obs = block.get_num_observed()[0]
            goodframes = 0
            for sublock in list(Block.objects.filter(superblock=block.id)):
                goodframes += sublock.num_unique_red_frames()
            if obs:
                if len(num_exps) > 1:
                    total_num = 0
                    for num in num_exps:
                        total_num += float(num[0])
                    framesoff = len(num_exps)-goodframes
                    total_num = total_num*((obs+framesoff)/len(num_exps))
                    long_obs = np.append(long_obs,[total_num,len_exps[0][0],block.tracking_number,block.body.current_name()])
                else:
                    total_num = goodframes
                    long_obs = np.append(long_obs,[total_num,len_exps[0][0],block.tracking_number,block.body.current_name()])

        long_obs = np.reshape(long_obs,(int(len(long_obs)/4),4))
        num_obs = 0
        for obs in long_obs:
            if float(obs[0])*float(obs[1]) >= options['total_time']:
                print('Block: %s Time observed: %.3f h  Object: %s' % (obs[2], float(obs[0])*float(obs[1])/3600, obs[3]))
                num_obs += 1
        print('Total observations: %i' % num_obs)
