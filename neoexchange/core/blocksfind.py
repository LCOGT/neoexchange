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

# An astrometric fit is considered good if the RMS is a real, positive value no
# larger than this (arcsec); SCAMP writes a NaN or a wild value when the fit
# falls over, so both cases are treated as failures.
DEFAULT_RMS_LIMIT = 0.3
# ...and if at least this many stars were used in the fit.
DEFAULT_MIN_FIT_STARS = 5
# Filter order for reporting; any others found are appended, sorted.
PREFERRED_FILTER_ORDER = ['gp', 'rp', 'ip', 'zs', 'zp', 'V', 'B', 'w']


def _is_real(value):
    '''
    Is <value> a real number i.e. not None and not a NaN ? Exploits the fact
    that with IEEE floating point, NaN values are not equal to themselves.
    '''
    return value is not None and value == value

def _mean_std(values):
    '''
    Returns the (mean, standard deviation, number) of the real (not None, not
    NaN) entries of <values>, or (NaN, NaN, 0) if there are none.
    '''
    clean = [v for v in values if _is_real(v)]
    if len(clean) == 0:
        return float('nan'), float('nan'), 0
    array = np.array(clean, dtype=float)
    # ddof=1 needs more than one point; a single frame has no spread to report
    std = array.std(ddof=1) if array.size > 1 else 0.0

    return array.mean(), std, array.size

def _ordered_filters(filters):
    '''
    Sort <filters> into the conventional order, with any unrecognized ones
    sorted and appended at the end.
    '''
    filters = list(filters)
    known = [f for f in PREFERRED_FILTER_ORDER if f in filters]

    return known + sorted(f for f in filters if f not in PREFERRED_FILTER_ORDER)


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

def find_didymos_blocks_by_groupid(groupid_prefix='65803_E10'):
    '''
    Routine to find all of the observed didymos blocks whose SuperBlock groupid
    starts with <groupid_prefix> (e.g. '65803_E10' for the FTS/E10 Didymos
    campaigns, whose group names are of the form '65803_E10_<YYYYMMDD>').
    Returns a QuerySet of matching Blocks, earliest first.
    '''
    blocks = Block.objects.filter(superblock__groupid__startswith=groupid_prefix)
    blocks = blocks.filter(num_observed__gte=1)

    return blocks.order_by('block_start')

def good_astrometric_fit(frame, rms_limit=DEFAULT_RMS_LIMIT, min_fit_stars=DEFAULT_MIN_FIT_STARS):
    '''
    Did <frame> get a usable astrometric fit ? Requires a real (not NaN/None),
    positive rms_of_fit no larger than <rms_limit> (arcsec) and at least
    <min_fit_stars> stars used in the fit.
    '''
    rms = frame.rms_of_fit
    num_stars = frame.nstars_in_fit
    if not _is_real(rms) or rms <= 0 or rms > rms_limit:
        return False
    if not _is_real(num_stars) or num_stars < min_fit_stars:
        return False

    return True

def good_zeropoint(frame):
    '''
    Did <frame> get a usable zeropoint ? Requires a real (not NaN/None),
    positive value; failed fits are stored as null or a -99 sentinel.
    '''
    return _is_real(frame.zeropoint) and frame.zeropoint > 0

def frame_quality_stats(frames, rms_limit=DEFAULT_RMS_LIMIT, min_fit_stars=DEFAULT_MIN_FIT_STARS):
    '''
    Compute per-filter quality statistics for the passed <frames>.
    Returns a dict of filter->dict with the number of frames, the number with a
    good astrometric fit and a good zeropoint, and the mean and standard
    deviation of the FWHM and zeropoint.

    Only frames with a good zeropoint contribute to the zeropoint statistics,
    otherwise the null/-99 values of the failures would drag the mean down.
    '''
    stats = {}
    for frame in frames:
        stats.setdefault(frame.filter, []).append(frame)

    results = {}
    for obs_filter in _ordered_filters(stats.keys()):
        filter_frames = stats[obs_filter]
        good_astrom = [f for f in filter_frames if good_astrometric_fit(f, rms_limit, min_fit_stars)]
        good_zps = [f for f in filter_frames if good_zeropoint(f)]
        fwhm_mean, fwhm_std, num_fwhm = _mean_std([f.fwhm for f in filter_frames])
        zp_mean, zp_std, num_zp = _mean_std([f.zeropoint for f in good_zps])
        results[obs_filter] = {'num_frames' : len(filter_frames),
                               'num_good_astrometry' : len(good_astrom),
                               'num_good_zeropoint' : len(good_zps),
                               'fwhm_mean' : fwhm_mean, 'fwhm_std' : fwhm_std, 'num_fwhm' : num_fwhm,
                               'zp_mean' : zp_mean, 'zp_std' : zp_std, 'num_zp' : num_zp,
                              }

    return results

def summarize_didymos_frame_quality(blocks=None, groupid_prefix='65803_E10',
                                     rms_limit=DEFAULT_RMS_LIMIT,
                                     min_fit_stars=DEFAULT_MIN_FIT_STARS,
                                     show_failures=True):
    '''
    Print a per-Block summary of the reduction and subtraction state of the
    observed Didymos Blocks in <blocks>. If <blocks> is None, the Blocks whose
    SuperBlock groupid starts with <groupid_prefix> are used.

    For each Block the number of e91 (BANZAI reduced), e92 (NEOx reduced) and
    e93 (NEOx DIA subtracted) Frames is reported, along with how many of the
    e92 and e93 Frames have a good astrometric fit and a good zeropoint, and
    the mean and standard deviation of the FWHM and zeropoint per filter.
    If <show_failures> is True, the filename and number of fitted stars of the
    Frames which failed the astrometric fit are also listed.

    Returns a dict of Block id->summary dict.
    '''
    if blocks is None:
        blocks = find_didymos_blocks_by_groupid(groupid_prefix)
    try:
        num_blocks = len(blocks)
    except TypeError:
        blocks = [blocks, ]
        num_blocks = len(blocks)

    print(f"Summarizing {num_blocks} Block(s)")
    print(f"Good astrometry: 0 < rms_of_fit <= {rms_limit} arcsec and "
          f"nstars_in_fit >= {min_fit_stars}; good zeropoint: zeropoint > 0")

    summaries = {}
    for block in blocks:
        # One query for both reduced levels; num_neox is the combined total but
        # can be indexed by frametype for the individual e92 and e93 counts.
        neox_frames, num_banzai, num_neox = find_frames(block,
                                                         frametype=[Frame.NEOX_RED_FRAMETYPE,
                                                                    Frame.NEOX_SUB_FRAMETYPE])
        num_e92 = num_neox[Frame.NEOX_RED_FRAMETYPE]
        num_e93 = num_neox[Frame.NEOX_SUB_FRAMETYPE]

        groupid = ''
        if block.superblock:
            groupid = block.superblock.groupid or ''
        block_start = block.block_start.strftime('%Y-%m-%d %H:%M') if block.block_start else '-'
        print()
        print(f"{groupid} Block {block.id}: Request # {block.request_number} "
              f"{block.site.upper()} {block_start}")
        print(f"  #e91={num_banzai:>4d} #e92={num_e92:>4d} #e93={num_e93:>4d}")

        block_summary = {'groupid' : groupid, 'num_e91' : num_banzai,
                         'num_e92' : num_e92, 'num_e93' : num_e93, 'filters' : {}}
        failures = []
        for frametype, label in ((Frame.NEOX_RED_FRAMETYPE, 'e92'), (Frame.NEOX_SUB_FRAMETYPE, 'e93')):
            frames = [f for f in neox_frames if f.frametype == frametype]
            if len(frames) == 0:
                continue
            filter_stats = frame_quality_stats(frames, rms_limit, min_fit_stars)
            block_summary['filters'][label] = filter_stats
            num_good_astrom = sum(s['num_good_astrometry'] for s in filter_stats.values())
            num_good_zp = sum(s['num_good_zeropoint'] for s in filter_stats.values())
            print(f"  {label}: good astrometry={num_good_astrom:>4d}/{len(frames):<4d} "
                  f"good zeropoint={num_good_zp:>4d}/{len(frames):<4d}")
            for obs_filter, stats in filter_stats.items():
                print(f"    {obs_filter:<4s} n={stats['num_frames']:>4d} "
                      f"astrom OK={stats['num_good_astrometry']:>4d} "
                      f"FWHM={stats['fwhm_mean']:>6.3f} +/- {stats['fwhm_std']:<6.3f} (n={stats['num_fwhm']:>3d}) "
                      f"ZP={stats['zp_mean']:>7.4f} +/- {stats['zp_std']:<6.4f} (n={stats['num_zp']:>3d})")
            failures += [(label, f) for f in frames
                         if not good_astrometric_fit(f, rms_limit, min_fit_stars)]

        block_summary['num_failed_astrometry'] = len(failures)
        if failures and show_failures:
            print(f"  Failed astrometric fit ({len(failures)} frame(s)):")
            for label, frame in failures:
                rms = frame.rms_of_fit if _is_real(frame.rms_of_fit) else float('nan')
                num_stars = int(frame.nstars_in_fit) if _is_real(frame.nstars_in_fit) else -1
                print(f"    {label} {frame.filename:<44s} {frame.filter:<4s} "
                      f"#fit stars={num_stars:>5d} rms_of_fit={rms:>8.3f}")
        summaries[block.id] = block_summary

    return summaries

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
        print(f"{block.request_number}: {block.block_start}->{block.block_end} {block.num_exposures:>3d}x{block.exp_length}s observed={block.num_observed} {block.site.upper()} ({proposal_code})")
        red_frames = block.frame_set.filter(frametype=Frame.NEOX_RED_FRAMETYPE)
        if red_frames:
            first_frame_midpoint = red_frames.earliest('midpoint').midpoint
            last_frame_midpoint = red_frames.latest('midpoint').midpoint
            print(f" Frames: {first_frame_midpoint.isoformat(timespec='seconds')}->{last_frame_midpoint.isoformat(timespec='seconds')}")

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

class FrameCounts(int):
    '''
    Total number of frames found, which can also be indexed by frametype to
    give the per-frametype breakdown.

    Behaves as the plain int total it has always been (so existing callers of
    find_frames() are unaffected), but additionally supports e.g.
    num_neox[Frame.NEOX_SUB_FRAMETYPE] to get just the e93 count.
    '''
    def __new__(cls, total, per_frametype=None):
        obj = super().__new__(cls, total)
        obj.per_frametype = dict(per_frametype or {})
        return obj

    def __getitem__(self, frametype):
        return self.per_frametype[frametype]

    def get(self, frametype, default=0):
        return self.per_frametype.get(frametype, default)

    def keys(self):
        return self.per_frametype.keys()

    def items(self):
        return self.per_frametype.items()


def find_frames(block, frametype = Frame.NEOX_RED_FRAMETYPE):
    '''
    Routine to find all frames for a given block as well as number of banzai
    frames and number of neox frames.
    Returns list of frames and number of banzai and neox frames.

    The number of neox frames is a FrameCounts, which is the total count (as
    it has always been) but can additionally be indexed by frametype to get
    the per-type breakdown, e.g.

        frames, num_banzai, num_neox = find_frames(block,
                                                   frametype=[Frame.NEOX_RED_FRAMETYPE,
                                                              Frame.NEOX_SUB_FRAMETYPE])
        num_neox                             # total of e92+e93 frames
        num_neox[Frame.NEOX_RED_FRAMETYPE]   # count of e92 frames only
        num_neox[Frame.NEOX_SUB_FRAMETYPE]   # count of e93 frames only

    This avoids having to call this routine once per frametype (which would
    also recount the BANZAI frames each time).
    '''
    frames = Frame.objects.filter(block=block)
    # Determine frame types to search for
    banzai_frame_types = [Frame.BANZAI_RED_FRAMETYPE, ]
    try:
        banzai_frame_types.append(Frame.MRO_RED_FRAMETYPE)
    except AttributeError:
        pass
    if type(frametype) != list:
        frametype = [frametype, ]
    banzai_frames = frames.filter(frametype__in=banzai_frame_types) #, rms_of_fit__gte=0.0)
    neox_frames = frames.filter(frametype__in=frametype)
    neox_frames = neox_frames.order_by('midpoint')
    #if len(banzai_frames) != len(neox_frames):
    #    print(f'Block uid: {block.get_blockuid}, Num banzai frames: {len(banzai_frames)}, Num neox frames: {len(neox_frames)}')

    # Only hit the database for the breakdown when more than one frametype was
    # asked for; for the single-type case it is just the total.
    if len(frametype) > 1:
        per_frametype = {ftype: neox_frames.filter(frametype=ftype).count() for ftype in frametype}
    else:
        per_frametype = {frametype[0]: neox_frames.count()}

    return neox_frames, banzai_frames.count(), FrameCounts(neox_frames.count(), per_frametype)

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

def ephem_interpolate(times, table, extra_quantity=None):
    '''
    Returns a list of interpolated values for both RA and DEC given a
    horizons_ephem <table> and a list of times(TimeJD or datetime)
    [extra_quantity] can be set to the name or an iterable of extra column
    names to also interpolate over.
    '''

    extra_arrays = {}
    if extra_quantity is not None and isinstance(extra_quantity, str):
        extra_quantity = [extra_quantity, ]
    try:
        arr1 = table['datetime_jd']
        arr2 = table['RA']
        arr3 = table['DEC']
    except KeyError:
        # sbpy Ephem object ?  let's try...
        arr1 = table['epoch'].jd
        arr2 = table['RA'].value
        arr3 = table['DEC'].value
    if extra_quantity is not None:
        for column in extra_quantity:
            if column in table.colnames:
                extra_arrays[column] = table[column].value

    start_time = arr1[0]
    end_time = arr1[-1]
    if isinstance(start_time, Time):
        start_time = start_time.jd
    if isinstance(end_time, Time):
        end_time = end_time.jd

    if isinstance(times, list) is False and isinstance(times, Time) is False:
        times = [times,]

    if isinstance(times[0], datetime):
        times = Time(times).jd
    elif isinstance(times[0], Time):
        times = times.jd # np.array([t.jd for t in times])

    if min(times) < start_time or max(times) > end_time:
        return [],[]

    result_RA = np.interp(times, arr1, arr2)
    result_DEC = np.interp(times, arr1, arr3)
    if extra_quantity is not None:
        extra_results = {}
        for key, arr4 in extra_arrays.items():
            extra_results[key] = np.interp(times, arr1, arr4)

    to_return = (result_RA, result_DEC)
    if extra_quantity is not None:
        to_return = result_RA, result_DEC, extra_results
    return to_return

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
