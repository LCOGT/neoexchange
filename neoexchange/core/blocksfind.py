from core.models import Body,Block,SuperBlock,Frame
from astropy.wcs import WCS, FITSFixedWarning, InvalidTransformError
from datetime import datetime,timedelta
import warnings
import calendar
from astropy.wcs import WCS, FITSFixedWarning, InvalidTransformError
from astrometrics.ephem_subs import horizons_ephem
from astropy.time import Time
import numpy as np
warnings.simplefilter('ignore', category=FITSFixedWarning)


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
    filtered_blocks = []
    dates = []
    for block in blocks:
        frames = find_frames(block)
        filter_frames = frames.order_by('filter').distinct('filter')
        if len(frames)>min_frames and len(frames)<max_frames and filter_frames.count()==1:
            filtered_blocks.append(block)
            dates.append(block.block_start)

    return filtered_blocks, dates

def find_frames(block):
    '''
    Routine to find all frames for a given block and number and type(s)
    of different filters
    Returns list of frames
    '''
    frames = Frame.objects.filter(block = block)
    frames = frames.filter(frametype = Frame.BANZAI_RED_FRAMETYPE)
    #frames = frames.filter(frametype = Frame.NEOX_RED_FRAMETYPE)
    frames = frames.order_by('midpoint')

    return frames


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
    didymos = Body.objects.get(name = '65803')
    frames = find_frames(block)
    #frames_summary(frames)
    first_frame = frames[0]
    last_frame = frames[frames.count()-1]
    onemin = timedelta(minutes = 1)
    delta_1 = timedelta(seconds = first_frame.exptime/2)
    delta_2 = timedelta(seconds = last_frame.exptime/2)
    table = horizons_ephem(didymos.current_name(), first_frame.midpoint - delta_1 - onemin, last_frame.midpoint + delta_2 + onemin, first_frame.sitecode, '1m')

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
