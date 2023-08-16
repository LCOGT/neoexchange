import logging
import os
from astropy.wcs import WCS, FITSFixedWarning, InvalidTransformError
from astropy.io import fits
from astropy.time import Time
from datetime import datetime,timedelta
import warnings
import calendar
from photutils.centroids import centroid_sources, centroid_2dg
import numpy as np
from astrometrics.ephem_subs import horizons_ephem
from core.models import Body,Block,SuperBlock,Frame
warnings.simplefilter('ignore', category=FITSFixedWarning)

logger = logging.getLogger(__name__)


def find_didymos_blocks():
    '''
    Routine to find all of the observed didymos blocks after time of impact
    and which are not part of the LCOEngineering or the SWOPE2022 proposals
    Returns list of matching blocks
    '''
    didymos = Body.objects.get(name = '65803')
    blocks = Block.objects.filter(body = didymos)
    blocks = blocks.filter(num_observed__gte=1)
    blocks = blocks.filter(block_start__gte = "2022-09-26T23:14")
    blocks = blocks.filter(obstype = Block.OPT_IMAGING)
    blocks = blocks.exclude(superblock__proposal__code__in=["LCOEngineering","SWOPE2022"]).order_by('block_start')

    return blocks

def blocks_summary(blocks):
    '''
    Prints short summary of passed <blocks>
    '''
    for block in blocks:
        sblock = block.superblock
        proposal_code = "none"
        if sblock:
            if sblock.proposal:
                proposal_code=sblock.proposal.code
        print(f"{block.block_start}->{block.block_end} {block.num_exposures}x{block.exp_length}s observed={block.num_observed} ({proposal_code})")

def split_light_curve_blocks(frames, exptime=800):
    '''
    Routine to split a light curve <block> into equal sized sub-blocks with
    total exposure time equal to <exptime>
    '''
    if len(frames)==0:
        return []
    exp_length = frames[0].block.exp_length
    #print(exp_length)
    total_exp_time = len(frames) * exp_length
    div_factor = total_exp_time/exptime
    split_block = np.array_split(frames, round(div_factor))

    return split_block

def get_substacks(subblock, segstack_sequence=7):
    '''
    Routine to get substacks for a given <subblock>. <subblock> should be 
    a list of frames. Returns the stacked filenames
    '''
    sorted_frames=[]
    for i in range(1, segstack_sequence+1):
        ii = i
        if i == segstack_sequence:
            ii=0
            #print('Reset')
        #print(i, ii)
        frames=[]
        for j in range(1, len(subblock)+1):
            if j%segstack_sequence==ii:
                #print(frames[j-1].filename)
                frames.append(subblock[j-1])
        sorted_frames.append(frames)
        #print(f'num frames: {int((j-i)/segstack_sequence)+1}')
        #print(f'output: substack-{i}')
    return sorted_frames

def filter_blocks(original_blocks, start_date, end_date, min_frames=3, max_frames=10):
    '''
    Routine to filter blocks in <original_blocks> . If <original_blocks> is None,
    then it calls find_didymos_blocks() to return a QuerySet of Blocks.

    Returns blocks that are between <start_date>
    and <end_date> and that have a number of frames between <min_frames> and
    <max_frames>.
    '''
    if original_blocks is None:
        didymos_blocks = find_didymos_blocks()
    else:
        didymos_blocks = original_blocks

    blocks = didymos_blocks.filter(block_start__gte = start_date)
    blocks = blocks.filter(block_end__lte = end_date)
    blocks = blocks.exclude(block_start__lte = "2022-09-27T04:00:00")
    filtered_blocks = []
    dates = []
    for block in blocks:
        frames, num_banzai, num_neox = find_frames(block)
        filter_frames = frames.order_by('filter').distinct('filter')
        if len(frames)>min_frames and len(frames)<max_frames and filter_frames.count()==1:
            filtered_blocks.append(block)
            dates.append(block.block_start)

    return filtered_blocks, dates

def find_frames(block):
    '''
    Routine to find all frames for a given block as well as number of banzai
    frames and number of neox frames. 
    Returns list of frames and number of banzai and neox frames.
    '''
    frames = Frame.objects.filter(block = block)
    banzai_frames = frames.filter(frametype = Frame.BANZAI_RED_FRAMETYPE)
    neox_frames = frames.filter(frametype = Frame.NEOX_RED_FRAMETYPE)
    neox_frames = neox_frames.order_by('midpoint')
    #if len(banzai_frames) != len(neox_frames):
    #    print(f'Block uid: {block.get_blockuid}, Num banzai frames: {len(banzai_frames)}, Num neox frames: {len(neox_frames)}')

    return neox_frames, len(banzai_frames), len(neox_frames)

def frames_summary(frames):
    '''
    Prints short summary of passed <frames>
    '''
    total_exptime = 0
    for frame in frames:
        delta = timedelta(seconds = frame.exptime/2)
        print(f"{frame.block.request_number}: {frame.midpoint - delta}->{frame.midpoint + delta}  exposure time:{frame.exptime}s")
        total_exptime = total_exptime + frame.exptime

    print(f"expected exposures: {frame.block.num_exposures}, executed exposures: {frames.count()}, total exposure time: {round(total_exptime, 2)}s")

    filter_frames = frames.order_by('filter').distinct('filter')
    filter_names = ", ".join(filter_frames.values_list('filter',flat=True))

    print(f"number of filters: {filter_frames.count()}, filter type(s): {filter_names}")

def get_ephem(block):
    '''
    Creates a horizons ephemeris table for a passed <block>
    '''
    body = block.body
    frames, num_banzai, num_neox = find_frames(block)
    #frames_summary(frames)
    first_frame = frames[0]
    last_frame = frames[frames.count()-1]
    onemin = timedelta(minutes = 1)
    delta_1 = timedelta(seconds = first_frame.exptime/2)
    delta_2 = timedelta(seconds = last_frame.exptime/2)
    start_time = first_frame.midpoint - delta_1 - onemin
    end_time = last_frame.midpoint + delta_2 + onemin
    if end_time < start_time:
        logger.warning("Start time is greater than end time")
    if first_frame.sitecode is None:
        logger.warning("First frame sitecode is missing or null")
    table = horizons_ephem(body.current_name(), start_time, end_time, first_frame.sitecode, '1m')

    return table

def ephem_interpolate(times, table):
    '''
    Returns a list of interpolated values for both RA and DEC given a
    horizons_ephem <table> and a list of times(TimeJD or datetime)
    '''
    arr1 = table['datetime_jd']
    arr2 = table['RA']
    arr3 = table['DEC']

    start_time = arr1[0]
    end_time = arr1[-1]

    if isinstance(times, list) is False:
        times = [times,]

    if isinstance(times[0], datetime):
        times = Time(times).jd

    if min(times) < start_time or max(times) > end_time:
        return [],[]

    result_RA = np.interp(times, arr1, arr2)
    result_DEC = np.interp(times, arr1, arr3)

    return result_RA, result_DEC

def get_centroid_difference(filename, orig_sci_dir):
    '''
    Returns the difference between the interpolated position of Didymos
    and the position found by photutils.centroid_sources for a given
    <filename>.
    '''
    raw_filename = os.path.basename(filename)
    if '-combine-superstack' in raw_filename:
        orig_raw_filename = raw_filename.replace('-combine-superstack','')
    else:
        orig_raw_filename = raw_filename.replace('-combine','')
    original_filename = os.path.join(orig_sci_dir, orig_raw_filename)

    hdulist = fits.open(filename)
    data = hdulist[1].data
    header = hdulist[1].header
    stack_wcs = WCS(header)

    width = header['NAXIS1']
    height = header['NAXIS2']
    xpos = width/2
    ypos = height/2

    orig_hdulist = fits.open(original_filename)
    orig_header = orig_hdulist['SCI'].header
    time = orig_header['DATE-OBS'] #start date of first frame in stack
    date = datetime.strptime(time, "%Y-%m-%dT%H:%M:%S.%f")

    req_num = orig_header['REQNUM']
    block = Block.objects.get(request_number = req_num)

    table = get_ephem(block)

    RA, DEC = ephem_interpolate(date, table)

    x_interp, y_interp = stack_wcs.world_to_pixel_values(RA, DEC)
    x_interp = x_interp[0]
    y_interp = y_interp[0]

    x, y = centroid_sources(data, xpos, ypos)
    x = x[0]
    y = y[0]

    x_diff = abs(x_interp - x)
    y_diff = abs(y_interp - y)

    return x_diff, y_diff
