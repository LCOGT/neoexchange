import time
from datetime import datetime, timedelta

import numpy as np

from core.models import Block, Body, Frame, SourceMeasurement, DataProduct

def summarize_observations(target_name='65803', start_date='2022-07-15'):

    didymos = Body.objects.get(name=target_name)
    blocks = Block.objects.filter(body=didymos, block_start__gte=start_date)
    filt_width = 3
    if blocks.filter(site='ogg', telclass='2m0').count() > 0:
        # Set wider width for MuSCAT blocks
        filt_width = 14
    for block in blocks.order_by('block_start'):
        all_raw_frames = Frame.objects.filter(block=block, frametype=Frame.BANZAI_RED_FRAMETYPE)
        all_frames = Frame.objects.filter(block=block, frametype=Frame.NEOX_RED_FRAMETYPE)
        num_good_zp = all_frames.filter(zeropoint__gte=0).count()
        num_raw_frames = all_raw_frames.count()
        num_all_frames = all_frames.count()
        srcs = SourceMeasurement.objects.filter(frame__block=block)
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
                srcs_snr = srcs.filter(frame__filter=obs_filter).values_list('snr',flat=True)
                snr = -999
                if len(srcs_snr) > 0:
                    snr = np.mean(srcs_snr)
                fwhm = -99
                srcs_fwhm = frames.values_list('fwhm', flat=True)
                num_dp = DataProduct.objects.filter(filetype=DataProduct.DART_TXT, object_id=block.superblock.pk).count()
                if len(srcs_fwhm) > 0:
                    fwhm = np.mean(srcs_fwhm)
                print(f'{block.superblock.tracking_number} {block.request_number} {block.site} ({first_frame.sitecode}) {block_start.strftime("%Y-%m-%d %H:%M")} -> {block_end.strftime("%Y-%m-%d %H:%M")} ({block_length_hrs:>4.2f} hrs) {block.superblock.get_obsdetails().replace(" secs", "s"):10s}({exp_length_hms}) {filter_str:{filt_width}s} {num_raw_frames:>3d}(e91)->{num_good_zp:>3d}/{num_all_frames:>3d} SNR= {snr:>6.1f} FWHM= {fwhm:.1f} DPs={num_dp}')

def examine_multiap():
    for aprad in np.arange(2,12):
        phot_file = os.path.join(input_dir, f"photometry_65803_Didymos__1996_GT_ap{aprad}.dat")
        table = read_photompipe_file(phot_file)
        mean_sig = table['in_sig'].mean()
        print(f"ap={aprad:02d} pix, mean_sig={mean_sig:.5f} SNR={1/mean_sig:.2f}")
