import time
import warnings
from datetime import datetime, timedelta

import numpy as np
from astropy.wcs import FITSFixedWarning

from core.models import Block, Body, Frame, SourceMeasurement, DataProduct

def summarize_observations(target_name='65803', start_date='2022-07-15', proposal=None, exclude_proposal=None, end_date=None, min_frames=1, return_blocks=False):

    # Suppress WCS obsfix warnings
    warnings.simplefilter('ignore', FITSFixedWarning)


    if type(target_name) != Body:
        target = Body.objects.get(name=target_name)
    else:
        target = target_name
    blocks = Block.objects.filter(body=target, block_start__gte=start_date)
    if proposal is not None:
        if type(proposal) == list:
            blocks = blocks.filter(superblock__proposal__code__in=proposal)
        else:
            blocks = blocks.filter(superblock__proposal__code=proposal)
    if exclude_proposal is not None:
        if type(proposal) == list:
            blocks = blocks.exclude(superblock__proposal__code__in=exclude_proposal)
        else:
            blocks = blocks.exclude(superblock__proposal__code=exclude_proposal)
    if end_date is not None:
        blocks = blocks.filter(block_end__lt=end_date)
    filt_width = 6
    filt_space = ''
    if blocks.filter(site__in=['ogg', 'coj'], telclass='2m0').count() > 0:
        # Set wider width for MuSCAT blocks
        filt_width = 8
        filt_space = '  '
    # Determine frame types to search for
    frame_types = [Frame.BANZAI_RED_FRAMETYPE, ]
    try:
        frame_types.append(Frame.SWOPE_RED_FRAMETYPE)
    except AttributeError:
        pass
    print(f'#Track# Rquest# Site(MPC)  Block start         Block end       Block length Obs details       Filter{filt_space} #raw #good_zp/#num all frames   FWHM   DPs')
    for block in blocks.order_by('block_start'):

        all_raw_frames = Frame.objects.filter(block=block, frametype__in=frame_types)
        all_frames = Frame.objects.filter(block=block, frametype=Frame.NEOX_RED_FRAMETYPE)
        num_good_zp = all_frames.filter(zeropoint__gte=0).count()
        num_raw_frames = all_raw_frames.count()
        num_all_frames = all_frames.count()
        srcs = SourceMeasurement.objects.filter(frame__block=block)
        block_length_hrs = -1
        username = block.superblock.proposal.pi
        if num_raw_frames > min_frames:
            filters = all_raw_frames.values_list('filter',flat=True).distinct()
            for obs_filter in filters:
                filter_str = obs_filter #", ".join(list(filters))
                raw_frames = all_raw_frames.filter(filter=obs_filter)
                num_raw_frames = raw_frames.count()
                frames = all_frames.filter(filter=obs_filter)
                num_good_zp = frames.filter(zeropoint__gte=0).count()
                num_all_frames = frames.count()
                first_frame = raw_frames.earliest('midpoint')
                block_start = first_frame.midpoint - timedelta(seconds=first_frame.exptime / 2.0)
                last_frame = raw_frames.latest('midpoint')
                block_end = last_frame.midpoint + timedelta(seconds=last_frame.exptime / 2.0)
                block_length = block_end - block_start
                block_length_hrs = block_length.total_seconds() / 3600.0
                exp_length_hms = time.strftime('%H:%M:%S', time.gmtime(block.exp_length))
                # Examine the instrument of `first_frame`; if its a MuSCAT frame,
                # add instrument into the filter string
                if first_frame.instrument.startswith('ep'):
                    filter_str += f'({first_frame.instrument})'
                srcs_snr = srcs.filter(frame__filter=obs_filter).exclude(snr__isnull=True).values_list('snr',flat=True)
                snr = -999
                if len(srcs_snr) > 0:
                    snr = np.mean(srcs_snr)
                fwhm = -99
                srcs_fwhm = frames.filter(fwhm__gt=0).exclude(fwhm__isnull=True).values_list('fwhm', flat=True)
                num_dp = DataProduct.objects.filter(filetype=DataProduct.DART_TXT, object_id=block.superblock.pk).count()
                if len(srcs_fwhm) > 0:
                    fwhm = np.mean(srcs_fwhm)
                print(f'{block.superblock.tracking_number} {block.request_number} {block.site} ({first_frame.sitecode}) {block_start.strftime("%Y-%m-%d %H:%M")} -> {block_end.strftime("%Y-%m-%d %H:%M")} ({block_length_hrs:>4.2f} hrs) {block.get_obsdetails().replace(" secs", "s"):10s}({exp_length_hms}) {filter_str:{filt_width}s} {num_raw_frames:>3d}(e91)->{num_good_zp:>3d}/{num_all_frames:>3d} SNR= {snr:>6.1f} {fwhm:>5.1f} DPs={num_dp} {block.superblock.proposal.code}')
#                print(f'{block.superblock.tracking_number} {block.request_number} {block.site} ({first_frame.sitecode}) {block_start.strftime("%Y-%m-%d %H:%M")} -> {block_end.strftime("%Y-%m-%d %H:%M")} ({block_length_hrs:>4.2f} hrs) {block.get_obsdetails().replace(" secs", "s"):10s}{filter_str:{filt_width}s} {num_raw_frames:>3d}(e91)->{num_good_zp:>3d}/{num_all_frames:>3d} SNR= {snr:>6.1f} {fwhm:>5.1f} {username:.26s}')
    if return_blocks:
        return blocks

def examine_multiap():
    for aprad in np.arange(2,12):
        phot_file = os.path.join(input_dir, f"photometry_65803_Didymos__1996_GT_ap{aprad}.dat")
        table = read_photompipe_file(phot_file)
        mean_sig = table['in_sig'].mean()
        print(f"ap={aprad:02d} pix, mean_sig={mean_sig:.5f} SNR={1/mean_sig:.2f}")
