"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2014-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""
from datetime import datetime, timedelta
from math import ceil
import os
import sys
import warnings

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from astropy.wcs import WCS, FITSFixedWarning
from urllib.parse import urljoin

from core.models import Block, Frame, Candidate, SourceMeasurement, Body
from core.models.blocks import NONLCO_SITES
from astrometrics.ephem_subs import LCOGT_domes_to_site_codes, LCOGT_site_codes
from astrometrics.time_subs import jd_utc2datetime
from core.urlsubs import get_lcogt_headers
from core.archive_subs import archive_login, check_for_archive_images, lco_api_call
from photometrics.catalog_subs import get_fits_files, open_fits_catalog, convert_value
import logging
import requests

logger = logging.getLogger('core')


def measurements_from_block(blockid, bodyid=None):
    block = Block.objects.get(pk=blockid)
    frames = Frame.objects.filter(block=block, frametype__in=(Frame.BANZAI_QL_FRAMETYPE, Frame.BANZAI_RED_FRAMETYPE, Frame.STACK_FRAMETYPE)).values_list('id', flat=True)
    measures = SourceMeasurement.objects.filter(frame__in=frames, obs_mag__gt=0.0).order_by('-body', 'frame__midpoint')
    if bodyid:
        measures = measures.filter(body__id=bodyid)
    bodies = measures.values_list('body', flat=True).distinct()
    extra_bodies = Body.objects.filter(id__in=bodies)
    return {'body': block.body, 'measures': measures, 'slot': block, 'extra_bodies': extra_bodies}


def find_images_for_block(blockid):
    """
    Look up Frames and Candidates in Block.
    Output all candidates coords for each frame for Light Monitor to display
    """
    red_frames = Frame.objects.filter(block__id=blockid, frametype=Frame.BANZAI_RED_FRAMETYPE).order_by('midpoint')
    ql_frames = Frame.objects.filter(block__id=blockid, frametype=Frame.BANZAI_QL_FRAMETYPE).order_by('midpoint')
    if red_frames.count() > 0 and red_frames.count() >= ql_frames.count():
        frames = red_frames
    else:
        frames = ql_frames
    candidates = candidates_by_block(blockid)
    img_list = []
    if not frames:
        return False
    x_size = frames[0].wcs._naxis1
    y_size = frames[0].wcs._naxis2
    if not frames[0].frameid:
        return False
    frames_list = [{'img': str(f.frameid)} for f in frames]
    return frames_list, candidates, x_size, y_size


def candidates_by_block(blockid):
    targets = []
    cands = Candidate.objects.filter(block__id=blockid).order_by('score')
    for cand in cands:
        coords = []
        sky_coords = []
        dets = cand.unpack_dets()
        times = [jd_utc2datetime(x).strftime("%Y-%m-%d %H:%M:%S") for x in dets['jd_obs']]
        d_zip = zip(dets['frame_number'], dets['x'], dets['y'], dets['ra'], dets['dec'], dets['mag'], times)
        for a in d_zip:
            coords.append({'x': a[1], 'y': a[2], 'time': a[6]})
            sky_coords.append({'ra': a[3] * 15.0, 'dec': a[4], 'mag': a[5]})
        motion = {'speed' : cand.convert_speed(), 'speed_raw' : cand.speed, 'pos_angle' : cand.sky_motion_pa}
        targets.append({'id': str(cand.id), 'coords': coords, 'sky_coords': sky_coords, 'motion': motion})
    return targets


def check_request_status(tracking_num=None):
    data_url = urljoin(settings.PORTAL_REQUEST_API, tracking_num)
    return lco_api_call(data_url)


def create_frame(params, block=None, frameid=None):
    # Return None if params is just whitespace
    if not params:
        return None

    if params.get('GROUPID', None):
        # In these cases we are parsing the FITS header
        frame_params = frame_params_from_header(params, block)
    elif params.get('ORIGIN', '') == 'LCO/OCIW':
        frame_params = frame_params_from_swope_header(params, block)
    else:
        # We are parsing observation logs
        frame_params = frame_params_from_log(params, block)

    if frameid is not None:
        # LCO data should always have an Archive/`frameid`
        frame_list = Frame.objects.filter(frameid=frameid)
        if frame_list.count() == 0:
            frame = Frame.objects.create(frameid=frameid, **frame_params)
            frame_created = True
        elif frame_list.count() == 1:
            frame = frame_list[0]
            frame_created = False
        else:
            msg = "Duplicate frames with frameid: " + frameid
            logger.error(msg)
            for frame in frame_list:
                logger.error(frame.id)
            raise Frame.MultipleObjectsReturned
    else:
        # Non-LCO data so need to match on less reliable midpoint
        try:
            frame_list = Frame.objects.filter(midpoint=frame_params['midpoint'])
            if len(frame_list) >= 1:
                frame_test = frame_list.filter(**frame_params)
                if frame_test:
                    frame = Frame.objects.get(**frame_params)
                    frame_created = False
                else:
                    logger.warning("Creating new Frame")
                    logger.warning(frame_params)
                    frame = Frame.objects.create(**frame_params)
                    frame_created = True
            else:
                frame = Frame.objects.create(**frame_params)
                frame_created = True
            frame.frameid = frameid
            frame.save()
        except Frame.MultipleObjectsReturned:
            logger.error("Duplicate frames:")
            frames = Frame.objects.filter(**frame_params)
            for frame in frames:
                logger.error(frame.id)
            raise Frame.MultipleObjectsReturned

    # Update catalogue information if we have it
    if params.get('astrometric_catalog', None):
        frame.astrometric_catalog = params.get('astrometric_catalog')
    if params.get('photometric_catalog', None):
        frame.photometric_catalog = params.get('photometric_catalog')
    if params.get('L1FWHM', None):
        fwhm = params.get('L1FWHM')
        if fwhm != 'NaN':
            frame.fwhm = fwhm
    frame.save()

    if frame_created:
        msg = "created"
    else:
        msg = "updated"
    logger.debug("Frame %s %s" % (frame, msg))
    return frame


def frame_params_from_header(params, block):
    # In these cases we are parsing the FITS header
    sitecode = LCOGT_domes_to_site_codes(params.get('SITEID', ''), params.get('ENCID', ''), params.get('TELID', ''))
    spectro_obstypes = ['ARC', 'LAMPFLAT', 'SPECTRUM']

    # Extract and convert reduction level to integer
    rlevel = params.get('RLEVEL', 0)
    try:
        rlevel = int(rlevel)
    except ValueError:
        logger.warning("Error converting RLEVEL to integer in frame " + params.get('ORIGNAME', None))
        rlevel = 0

    dateobs_keyword = 'DATE-OBS'
    if dateobs_keyword not in params:
        dateobs_keyword = 'DATE_OBS'
        if dateobs_keyword not in params:
            logger.error("Neither DATE-OBS or DATE_OBS found in header")
            return None

    frame_params = { 'midpoint' : params.get(dateobs_keyword, None),
                     'sitecode' : sitecode,
                     'filter'   : params.get('FILTER', "B"),
                     'frametype': rlevel,
                     'block'    : block,
                     'instrument': params.get('INSTRUME', None),
                     'filename'  : params.get('ORIGNAME', None),
                     'exptime'   : params.get('EXPTIME', None),
                 }

    inst_mode = params.get('CONFMODE', None)
    if inst_mode and inst_mode not in ['default', 'full_frame']:
        frame_params['extrainfo'] = inst_mode

    # correct exptime to actual shutter open duration
    shutter_open = params.get(dateobs_keyword, None)
    shutter_close = params.get('UTSTOP', None)
    if shutter_open and shutter_close:
        # start by assuming shutter closed on the same day it opened.
        shutter_close = shutter_open.split('T')[0] + 'T' + shutter_close
        # convert to datetime object
        try:
            shutter_open = datetime.strptime(shutter_open, "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            shutter_open = datetime.strptime(shutter_open, "%Y-%m-%dT%H:%M:%S")
        try:
            shutter_close = datetime.strptime(shutter_close, "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            shutter_close = datetime.strptime(shutter_close, "%Y-%m-%dT%H:%M:%S")
        # Increment close-time by 1 day if close happened before open
        if shutter_close < shutter_open:
            shutter_close = shutter_close + timedelta(days=1)
        # Calculate exposure time and save to frame.
        exptime = shutter_close - shutter_open
        exptime = exptime.total_seconds()
        exp_diff = abs(exptime - float(frame_params['exptime']))
        if exp_diff > 0.5 or exp_diff > exptime * 0.1:
            # If FLOYDS data, subtract readtime from exposure time. Otherwise, label as problematic.
            if params.get('OBSTYPE', 'EXPOSE').upper() in spectro_obstypes:
                exptime = max(exptime - 21., 0)
            else:
                frame_params['quality'] = 'ABORTED'
                logger.warning("Actual exposure time ({}s) differs significantly from requested exposure time ({}s) for {}.".format(exptime, frame_params['exptime'], frame_params['filename']))
        frame_params['exptime'] = exptime

    # Make adjustments for spectroscopy frames
    if params.get('OBSTYPE', 'EXPOSE').upper() in spectro_obstypes:
        aperture_type = params.get('APERTYPE', 'SLIT').rstrip()
        aperture_length = params.get('APERLEN', 'UNKNOWN')
        aperture_width = params.get('APERWID', 'UNK')
        length_str = 'UNK'
        if aperture_length != 'UNKNOWN':
            if aperture_length != '':
                length_str = "{0:.1f}".format(aperture_length)
        width_str = 'UNK'
        if aperture_width != 'UNKNOWN':
            if aperture_width != '':
                width_str = "{0:.1f}".format(aperture_width)
        slit_name = "{type:s}_{length:s}x{width:s}AS".format(type=aperture_type,
            length=length_str, width=width_str)
        frame_params['filter'] = slit_name
        frame_params['frametype'] = Frame.SPECTRUM_FRAMETYPE
        # XXX Replace (non-existant) L1FWHM with AGFWHM?

    # Try and create a WCS object from the header. If successful, add to frame
    # params
    wcs = None
    try:
        # Suppress warnings from newer astropy versions which raise
        # FITSFixedWarning on the lack of OBSGEO-L,-B,-H keywords even
        # though we have OBSGEO-X,-Y,-Z as recommended by the FITS
        # Paper VII standard...
        warnings.simplefilter('ignore', category = FITSFixedWarning)
        wcs = WCS(params)
        frame_params['wcs'] = wcs
    except ValueError:
        logger.warning("Error creating WCS entry from frameid=%s" % frameid)

    # Correct filename for missing trailing .fits extension
    if '.fits' not in frame_params['filename']:
        frame_params['filename'] = frame_params['filename'].rstrip() + '.fits'
    frame_extn = "{0:02d}.fits".format(rlevel)
    frame_params['filename'] = frame_params['filename'].replace('00.fits', frame_extn)
    # Correct midpoint for 1/2 the exposure time
    if frame_params['midpoint'] and frame_params['exptime']:
        try:
            midpoint = datetime.strptime(frame_params['midpoint'], "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            midpoint = datetime.strptime(frame_params['midpoint'], "%Y-%m-%dT%H:%M:%S")

        midpoint = midpoint + timedelta(seconds=float(frame_params['exptime']) / 2.0)
        frame_params['midpoint'] = midpoint
    return frame_params


def frame_params_from_swope_header(params, block):
    # In these cases we are parsing the Swope FITS header
    sitecode = '304'
    rlevel = Frame.SWOPE_RED_FRAMETYPE

    dateobs_keyword = 'DATE-OBS'
    inst_codes = {'Direct/4Kx4K-4' : 'D4K4' }

    frame_params = { 'midpoint' : params.get(dateobs_keyword, None),
                     'sitecode' : sitecode,
                     'filter'   : params.get('FILTER', "B"),
                     'frametype': rlevel,
                     'block'    : block,
                     'instrument': inst_codes.get(params.get('INSTRUME', None), 'D4K4'),
                     'filename'  : params.get('FILENAME', None),
                     'exptime'   : params.get('EXPTIME', None),
                 }

    inst_mode = params.get('SUBRASTR', None)
    if inst_mode and inst_mode not in ['none', ]:
        frame_params['extrainfo'] = inst_mode

    # Try and create a WCS object from the header. If successful, add to frame
    # params
    wcs = None
    try:
        # Suppress warnings from newer astropy versions which raise
        # FITSFixedWarning on the lack of OBSGEO-L,-B,-H keywords even
        # though we have OBSGEO-X,-Y,-Z as recommended by the FITS
        # Paper VII standard...
        warnings.simplefilter('ignore', category = FITSFixedWarning)
        wcs = WCS(params)
        frame_params['wcs'] = wcs
    except ValueError:
        logger.warning("Error creating WCS entry from frameid=%s" % frameid)

    # Correct filename for missing trailing .fits extension
    if '.fits' not in frame_params['filename']:
        frame_params['filename'] = frame_params['filename'].rstrip() + '.fits'
    # Correct midpoint for 1/2 the exposure time
    if frame_params['midpoint'] and frame_params['exptime']:
        try:
            midpoint = datetime.strptime(frame_params['midpoint'], "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            midpoint = datetime.strptime(frame_params['midpoint'], "%Y-%m-%dT%H:%M:%S")

        midpoint = midpoint + timedelta(seconds=float(frame_params['exptime']) / 2.0)
        frame_params['midpoint'] = midpoint
    return frame_params


def frame_params_from_log(params, block):
    # Called when parsing MPC NEOCP observations lines/logs
    our_site_codes = LCOGT_site_codes()
    # We are parsing observation logs
    sitecode = params.get('site_code', None)
    if sitecode in our_site_codes:
        if params.get('flags', None) != 'K':
            frame_type = Frame.SINGLE_FRAMETYPE
        else:
            frame_type = Frame.STACK_FRAMETYPE
    else:
        if params.get('obs_type', None) == 'S' or params.get('obs_type', None) == 's':
            frame_type = Frame.SATELLITE_FRAMETYPE
        else:
            frame_type = Frame.NONLCO_FRAMETYPE
    frame_params = { 'midpoint' : params.get('obs_date', None),
                     'sitecode' : sitecode,
                     'block'    : block,
                     'filter'   : params.get('filter', "B"),
                     'frametype' : frame_type,
                     'extrainfo' : params.get('obs_type', None)
                   }
    return frame_params


def ingest_frames(images, block):
    """
    Create Frame objects for each of the images in <images> and associate
    them with the passed Block <block>.
    - Also find out how many scheduler blocks were used
    """
    sched_blocks = []
    for image in images:
        if type(image.get('headers', None)) == str:
            # A string with a URL for retrieving headers
            image_header = lco_api_call(image.get('headers', None))
        else:
            # Header included already as a dict
            image_header = image['headers']
        if image_header:
            frame = create_frame(image_header['data'], block, image['id'])
            sched_blocks.append(image_header['data']['BLKUID'])
        else:
            logger.error("Could not obtain header for %s" % image)
    logger.debug("Ingested %s frames" % len(images))
    block_ids = set(sched_blocks)
    return block_ids


def images_from_fits(datapath, match_pattern='r*.fits'):
    """Assemble a similar `list` of images from FITS file matching the pattern
    [match_pattern] in <datapath> as would be returned by check_for_archive_images()
    """

    images = []
    fits_files = get_fits_files(datapath, match_pattern)

    for fits_file in fits_files:
        image = { 'id' : None, 'basename' : os.path.basename(fits_file) }
        fits_header, dummy_table, cattype = open_fits_catalog(fits_file, header_only=True)
        image['headers'] = {'data' : dict(fits_header.items()) }
        if 'BLKUID' not in image['headers']['data'] and 'NIGHT' in image['headers']['data']:
            image['headers']['data']['BLKUID'] = convert_value('request_number', image['headers']['data']['NIGHT'])
            image['headers']['data']['FILENAME'] = image['basename']
        images.append(image)

    return images

def block_status(block_id, datapath=None):
    """
    Check if a block has been observed. If it has, record when the longest run finished
    - RequestDB API is used for block status
    - FrameDB API is used for number and datestamp of images
    - We do not count scheduler blocks which include < 3 exposures
    """
    status = False
    try:
        block = Block.objects.get(id=block_id)
        try:
            tracking_num = block.superblock.tracking_number
        except AttributeError:
            logger.error("Superblock for Block with id %s does not exist" % block_id)
            return False
    except ObjectDoesNotExist:
        logger.error("Block with id %s does not exist" % block_id)
        return False

    obj_name = block.current_name()

    if block.site.lower() in NONLCO_SITES and datapath is not None:
        # Fake an obs portal/Valhalla status response
        data = { 'requests' : [{'id' : block.request_number,
                                'configurations' : [{'instrument_configs' : [{'exposure_count' : 1}],
                                                     'type' : 'REPEAT_EXPOSE'}
                                                   ]
                              } ]
                }
    else:
        # Get authentication token for Valhalla
        logger.info("Checking request status for block/track# %s / %s" % (block_id, tracking_num))
        data = check_request_status(tracking_num)
        # data is a full LCO request dict for this tracking number (now called 'id').
        if not data:
            logger.warning("Got no data for block/track# %s / %s" % (block_id, tracking_num))
            return False
        # Check if the request was not found
        if data.get('detail', 'None') == u'Not found.':
            logger.warning("Request not found for block/track# %s / %s" % (block_id, tracking_num))
            return False
        # Check if credentials provided
        if data.get('detail', 'None') == u'Invalid token header. No credentials provided.':
            logger.error("No VALHALLA_TOKEN set")
            return False

    # This loops through all BLOCKS in the SUPERBLOCK so we need to filter out 
    # only the one block used to call this procedure.
    exposure_count = 0
    for r in data['requests']:
        if r['id'] == int(block.request_number) or len(data['requests']) < 2:
            obstype = 'EXPOSE'
            try:
                if block.obstype == Block.OPT_SPECTRA or block.obstype == Block.OPT_SPECTRA_CALIB:
                    # Set OBSTYPE to null string for archive search so we get all
                    # types of frames
                    obstype = ''
            except AttributeError:
                logger.warning("Unable to find observation type for Block/track# %s / %s" % (block_id, tracking_num))

            if block.site.lower() in NONLCO_SITES and datapath is not None:
                # Non-LCO data, get images from walking directory of FITS filrs
                images = images_from_fits(datapath)
                last_image_header = images[-1].get('headers', {})
                num_archive_frames = len(images)
            else:
                # Query LCO archive for images
                images, num_archive_frames = check_for_archive_images(request_id=r['id'], obstype=obstype, obj='') #obj_name)
                logger.info('Request no. %s x %s images (%s total all red. levels)' % (r['id'], len(images), num_archive_frames))
            if images:
                inst_configs = [x['instrument_configs'] for x in r['configurations']]
                exposure_count = sum([x[0]['exposure_count'] for x in inst_configs])
                obs_types = [x['type'] for x in r['configurations']]
                if last_image_header is None:
                    # Look in the archive at the header of the most recent frame for a timestamp of the observation
                    # If we read FITS headers from files, we already have last_image_header
                    last_image_dict = images[0]
                    last_image_header = lco_api_call(last_image_dict.get('headers', None))
                if last_image_header is None:
                    logger.error('Image header was not returned for %s' % last_image_dict)
                    return False
                # At some point in Feb 2022, archive started returning data with DATE-OBS rather than DATE_OBS
                dateobs_keyword = 'DATE-OBS'
                if dateobs_keyword not in last_image_header['data']:
                    dateobs_keyword = 'DATE_OBS'
                    if dateobs_keyword not in last_image_header['data']:
                        logger.error("Neither DATE-OBS or DATE_OBS found in header")
                        return False

                try:
                    last_image = datetime.strptime(last_image_header['data'][dateobs_keyword][:19], '%Y-%m-%dT%H:%M:%S')
                except ValueError:
                    logger.error('Image datetime stamp is badly formatted %s' % last_image_header['data'][dateobs_keyword])
                    return False
                if not block.when_observed or last_image > block.when_observed:
                    block.when_observed = last_image
                # If the block end time has passed and we got all of the images, set to inactive.
                # N.B. we don't check against acceptability_threshold x expected no. of frames
                # to avoid race conditions where we have more than e.g. 90% of the frames but
                # there has been a delay in getting data back, the block_end has passed and
                # there may be more frames still to come in.
                if block.block_end < datetime.utcnow() and num_archive_frames == exposure_count * 2:
                    logger.info("All reduced frames found and block end passed - setting to inactive")
                    block.active = False
                # Add frames and get list of scheduler block IDs used
                block_ids = ingest_frames(images, block)

                # If we got at least 3 frames (i.e. usable for astrometry reporting) and
                # at least frames for at least one block were ingested, update the blocks'
                # observed count.
                if len(images) > block.num_exposures:
                    block.num_exposures = len(images)
                    logger.info("Updating num_exposures")
                if len(images) >= 1 and 'SPECTRUM' in obs_types and len(block_ids) >= 1:
                    logger.info("Spectra data found - setting to observed")
                    block.num_observed = len(block_ids)
                elif len(images) >= 3 and len(block_ids) >= 1:
                    logger.info("More than 3 reduced frames found - setting to observed")
                    block.num_observed = len(block_ids)
                block.save()
                status = True
                logger.info("Block #%d (%s) updated" % (block.id, block))
            else:
                logger.info("No update to block %s" % block)
    return status
