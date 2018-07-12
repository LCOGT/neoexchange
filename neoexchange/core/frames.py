"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2014-2018 LCO

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
import sys

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from astropy.wcs import WCS
from urllib.parse import urljoin

from core.models import Block, Frame, Candidate, SourceMeasurement, Body
from astrometrics.ephem_subs import LCOGT_domes_to_site_codes, LCOGT_site_codes
from astrometrics.time_subs import jd_utc2datetime
from core.urlsubs import get_lcogt_headers
from core.archive_subs import archive_login, check_for_archive_images, lco_api_call
import logging
import requests

logger = logging.getLogger('core')


def measurements_from_block(blockid, bodyid=None):
    block = Block.objects.get(pk=blockid)
    frames = Frame.objects.filter(block=block, frametype__in=(Frame.BANZAI_QL_FRAMETYPE, Frame.BANZAI_RED_FRAMETYPE, Frame.STACK_FRAMETYPE)).values_list('id',flat=True)
    measures = SourceMeasurement.objects.filter(frame__in=frames, obs_mag__gt=0.0).order_by('-body','frame__midpoint')
    if bodyid:
        measures = measures.filter(body__id=bodyid)
    bodies = measures.values_list('body', flat=True).distinct()
    extra_bodies = Body.objects.filter(id__in=bodies)
    return {'body' : block.body, 'measures' : measures, 'slot' : block,'extra_bodies':extra_bodies}

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
    frames_list = [{'img':str(f.frameid)} for f in frames]
    return frames_list, candidates, x_size, y_size

def candidates_by_block(blockid):
    targets = []
    cands = Candidate.objects.filter(block__id=blockid).order_by('score')
    for cand in cands:
        coords = []
        sky_coords = []
        dets = cand.unpack_dets()
        times = [jd_utc2datetime(x).strftime("%Y-%m-%d %H:%M:%S") for x in dets['jd_obs']]
        d_zip = zip(dets['frame_number'], dets['x'], dets['y'], dets['ra'], dets['dec'], dets['mag'], times )
        for a in d_zip:
            coords.append({'x':a[1], 'y':a[2], 'time':a[6]})
            sky_coords.append({'ra':a[3] * 15.0, 'dec':a[4], 'mag':a[5]})
        motion = {'speed' : cand.convert_speed(), 'speed_raw' : cand.speed, 'pos_angle' : cand.sky_motion_pa}
        targets.append({'id': str(cand.id), 'coords':coords, 'sky_coords':sky_coords, 'motion':motion})
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
    else:
        # We are parsing observation logs
        frame_params = frame_params_from_log(params, block)

    try:
        frame, frame_created = Frame.objects.get_or_create(**frame_params)
        frame.frameid = frameid
        frame.save()
    except Frame.MultipleObjectsReturned:
        logger.error("Duplicate frames:")
        frames = Frame.objects.filter(**frame_params)
        for frame in frames:
            logger.error(frame.id)
        raise(Frame.MultipleObjectsReturned)

    # Update catalogue information if we have it
    if params.get('astrometric_catalog',None):
        frame.astrometric_catalog = params.get('astrometric_catalog')
        frame.save()
    if params.get('photometric_catalog',None):
        frame.photometric_catalog = params.get('photometric_catalog')
        frame.save()

    if frame_created:
        msg = "created"
    else:
        msg = "updated"
    logger.debug("Frame %s %s" % (frame, msg))
    return frame

def frame_params_from_header(params, block):
    # In these cases we are parsing the FITS header
    sitecode = LCOGT_domes_to_site_codes(params.get('SITEID', None), params.get('ENCID', None), params.get('TELID', None))
    spectro_obstypes = ['ARC', 'LAMPFLAT', 'SPECTRUM']

    frame_params = { 'midpoint' : params.get('DATE_OBS', None),
                     'sitecode' : sitecode,
                     'filter'   : params.get('FILTER', "B"),
                     'frametype': params.get('RLEVEL', 0),
                     'block'    : block,
                     'instrument': params.get('INSTRUME', None),
                     'filename'  : params.get('ORIGNAME', None),
                     'exptime'   : params.get('EXPTIME', None),
                     'fwhm'      : params.get('L1FWHM', None),
                 }
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
        wcs = WCS(params)
        frame_params['wcs'] = wcs
    except ValueError:
        logger.warning("Error creating WCS entry from frameid=%s" % frameid)


    # Correct filename for missing trailing .fits extension
    if '.fits' not in frame_params['filename']:
        frame_params['filename'] = frame_params['filename'].rstrip() + '.fits'
    rlevel = params.get('RLEVEL', 0)
    frame_extn = "{0:02d}.fits".format(rlevel)
    frame_params['filename'] = frame_params['filename'].replace('00.fits', frame_extn)
    # Correct midpoint for 1/2 the exposure time
    if frame_params['midpoint'] and frame_params['exptime']:
        try:
            midpoint = datetime.strptime(frame_params['midpoint'], "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            midpoint = datetime.strptime(frame_params['midpoint'], "%Y-%m-%dT%H:M:%S")

        midpoint = midpoint + timedelta(seconds=float(frame_params['exptime']) / 2.0)
        frame_params['midpoint'] = midpoint
    return frame_params

def frame_params_from_block(params, block):
    # In these cases we are parsing the Block info
    sitecode = LCOGT_domes_to_site_codes(params.get('siteid', None), params.get('encid', None), params.get('telid', None))
    frame_params = { 'midpoint' : params.get('date_obs', None),
                     'sitecode' : sitecode,
                     'filter'   : params.get('filter_name', "B"),
                     'frametype': Frame.SINGLE_FRAMETYPE,
                     'block'    : block,
                     'instrument': params.get('instrume', None),
                     'filename'  : params.get('origname', None),
                     'exptime'   : params.get('exptime', None),
                 }
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
                     'frametype' : frame_type
                   }
    return frame_params


def ingest_frames(images, block):
    '''
    Create Frame objects for each of the images in <images> and associate
    them with the passed Block <block>.
    - Also find out how many scheduler blocks were used
    '''
    sched_blocks = []
    for image in images:
        image_header = lco_api_call(image.get('headers', None))
        if image_header:
            frame = create_frame(image_header['data'], block, image['id'])
            sched_blocks.append(image_header['data']['BLKUID'])
        else:
            logger.error("Could not obtain header for %s" % image)
    logger.debug("Ingested %s frames" % len(images))
    block_ids = set(sched_blocks)
    return block_ids

def block_status(block_id):
    '''
    Check if a block has been observed. If it has, record when the longest run finished
    - RequestDB API is used for block status
    - FrameDB API is used for number and datestamp of images
    - We do not count scheduler blocks which include < 3 exposures
    '''
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
    #only the one block used to call this procedure.
    exposure_count = 0
    for r in data['requests']:
        if r['id'] == int(block.tracking_number) or len(data['requests']) < 2:
            obstype = 'EXPOSE'
            try:
                if block.obstype == Block.OPT_SPECTRA:
                    # Set OBSTYPE to null string for archive search so we get all
                    # types of frames
                    obstype = ''
            except AttributeError:
                logger.warn("Unable to find observation type for Block/track# %s / %s" % (block_id, tracking_num))
            images, num_archive_frames = check_for_archive_images(request_id=r['id'], obstype=obstype)
            logger.info('Request no. %s x %s images (%s total all red. levels)' % (r['id'], len(images), num_archive_frames))
            if images:
                exposure_count = sum([x['exposure_count'] for x in r['molecules']])
                obs_types = [x['type'] for x in r['molecules']]
                # Look in the archive at the header of the most recent frame for a timestamp of the observation
                last_image_dict = images[0]
                last_image_header = lco_api_call(last_image_dict.get('headers', None))
                if last_image_header == None:
                    logger.error('Image header was not returned for %s' % last_image_dict)
                    return False
                try:
                    last_image = datetime.strptime(last_image_header['data']['DATE_OBS'][:19],'%Y-%m-%dT%H:%M:%S')
                except ValueError:
                    logger.error('Image datetime stamp is badly formatted %s' % last_image_header['data']['DATE_OBS'])
                    return False
                if (not block.when_observed or last_image > block.when_observed):
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
                if len(images) >= 3 and len(block_ids) >= 1:
                    logger.info("More than 3 reduced frames found - setting to observed")
                    block.num_observed = len(block_ids)
                elif len(images) >=1 and 'SPECTRUM' in obs_types and len(block_ids) >= 1:
                    logger.info("Spectra data found - setting to observed")
                    block.num_observed = len(block_ids)
                block.save()
                status = True
                logger.info("Block #%d (%s) updated" % (block.id, block))
            else:
                logger.info("No update to block %s" % block)
    return status
