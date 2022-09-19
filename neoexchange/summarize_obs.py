import time
from datetime import datetime, timedelta

import numpy as np

from core.models import Block, Body, Frame

def summarize_observations(target_name='65803', start_date='2022-07-15'):

    didymos = Body.objects.get(name=target_name)
    blocks = Block.objects.filter(body=didymos, block_start__gte=start_date)
    filt_width = 6
    if blocks.filter(site='ogg', telclass='2m0').count() > 0:
        # Set wider width for MuSCAT blocks
        filt_width = 14
    for block in blocks.order_by('-block_start'):
        all_frames = Frame.objects.filter(block=block, frametype=Frame.BANZAI_RED_FRAMETYPE)
        num_good_zp = all_frames.filter(zeropoint__gte=0).count()
        num_all_frames = all_frames.count()
        block_length_hrs = -1
        if num_all_frames > 1:
            filters = all_frames.values_list('filter',flat=True).distinct()
            for obs_filter in filters:
                filter_str = obs_filter #", ".join(list(filters))
                frames = all_frames.filter(filter=obs_filter)
                num_good_zp = frames.filter(zeropoint__gte=0).count()
                num_all_frames = frames.count()
                first_frame = frames.earliest('midpoint')
                block_start = first_frame.midpoint - timedelta(seconds=first_frame.exptime / 2.0)
                last_frame = frames.latest('midpoint')
                block_end = last_frame.midpoint + timedelta(seconds=last_frame.exptime / 2.0)
                block_length = block_end - block_start
                block_length_hrs = block_length.total_seconds() / 3600.0
                exp_length_hms = time.strftime('%H:%M:%S', time.gmtime(block.exp_length))
                print(f'{block.id} {block.site} {block_start.strftime("%Y-%m-%d %H:%M")} -> {block_end.strftime("%Y-%m-%d %H:%M")} ({block_length_hrs:>5.2f} hrs) {block.superblock.get_obsdetails():14s} ({exp_length_hms}) {filter_str:{filt_width}s} {num_good_zp: 3d}/{num_all_frames: 3d}')

def examine_multiap():
    for aprad in np.arange(2,12):
        phot_file = os.path.join(input_dir, f"photometry_65803_Didymos__1996_GT_ap{aprad}.dat")
        table = read_photompipe_file(phot_file)
        mean_sig = table['in_sig'].mean()
        print(f"ap={aprad:02d} pix, mean_sig={mean_sig:.5f} SNR={1/mean_sig:.2f}")
