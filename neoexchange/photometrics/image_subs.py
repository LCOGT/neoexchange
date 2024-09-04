"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2016-2019 LCO

image_subs.py -- Code to create weight images for SWarp from the rms images generated by SExtractor.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""
import os
import logging
from glob import glob

import numpy as np
import astropy.units as u
from astropy.io import fits
from astropy.wcs import WCS
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.stats import sigma_clipped_stats
from core.models import StaticSource, Block, Frame

logger = logging.getLogger(__name__)


def get_cd(header_or_wcs):
    """Return the coordinate conversion matrix (CD).

    This is a 2x2 matrix that can be used to convert from the column and
    row indexes of a pixel in the image array to a coordinate within a flat
    map-projection of the celestial sphere.
    Routine adapted from the mpdaf.obj.coords"""

    if type(header_or_wcs) == dict and 'wcs' in header_or_wcs:
        wcs = header_or_wcs['wcs']
    elif type(header_or_wcs) == fits.Header:
        wcs = WCS(header_or_wcs)
    else:
        wcs = header_or_wcs

    # The documentation for astropy.wcs.Wcsprm indicates that
    # get_cdelt() and get_pc() work:
    #
    # "even when the header specifies the linear transformation
    #  matrix in one of the alternative CDi_ja or CROTAia
    #  forms. This is useful when you want access to the linear
    #  transformation matrix, but don't care how it was specified
    #  in the header."
    return np.dot(np.diag(wcs.wcs.get_cdelt()), wcs.wcs.get_pc())

def image_angle_from_cd(cd, unit=u.deg):
    """Return the rotation angle of the image.

    Defined such that a rotation angle of zero aligns north along the positive
    Y axis, and a positive rotation angle rotates north away from the Y axis,
    in the sense of a rotation from north to east.

    Note that the rotation angle is defined in a flat map-projection of the
    sky. It is what would be seen if the pixels of the image were drawn with
    their pixel widths scaled by the angular pixel increments returned by the
    axis_increments_from_cd() method.

    If the CD matrix was derived from the archaic CROTA and CDELT FITS
    keywords, then the angle returned by this function is equal to CROTA.

    Parameters
    ----------
    cd : numpy.ndarray
        The 2x2 coordinate conversion matrix, with its elements
        ordered for multiplying a column vector in FITS (x,y) axis order.
    unit : `astropy.units.Unit`
        The unit to give the returned angle (degrees by default).

    Returns
    -------
    out : float
        The angle between celestial north and the Y axis of the image,
        in the sense of an eastward rotation of celestial north from
        the Y-axis. The angle is returned in the range -180 to 180
        degrees (or the equivalent for the specified unit).

    """

    # Get the angular increments of pixels along the Y and X axes
    ## Calculate the width and height of the pixels.
    dx = np.sqrt(cd[0, 0]**2 + cd[1, 0]**2)
    dy = np.sqrt(cd[0, 1]**2 + cd[1, 1]**2)

    ## Get the determinant of the coordinate transformation matrix.
    cddet = np.linalg.det(cd)

    ## Calculate the rotation angle of a unit northward vector
    ## clockwise of the Y axis.
    north = np.arctan2(-cd[0, 1] / cddet, cd[0, 0] / cddet)

    ## Calculate the rotation angle of a unit eastward vector
    ## clockwise of the Y axis.
    east = np.arctan2(cd[1, 1] / cddet, -cd[1, 0] / cddet)

    # Wrap the difference east-north into the range -pi to pi radians.
    from astropy.coordinates import Angle
    delta = Angle((east - north) * u.rad).wrap_at(np.pi * u.rad).value

    # If east is anticlockwise of north make the X-axis pixel increment
    # negative.
    if delta < 0.0:
        dx *= -1.0
    step = np.array([dy, dx])

    # The angle of a northward vector from the origin can be calculated by
    # first using the inverse of the CD matrix to calculate the equivalent
    # vector in pixel indexes, then calculating the angle of this vector to the
    # Y axis of the image array.
    north = np.arctan2(-cd[0, 1] * step[1] / cddet,
                        cd[0, 0] * step[0] / cddet)

    # Return the angle with the specified units.
    return (north * u.rad).to(unit).value

def get_rot(header_or_wcs, unit=u.deg):
        """Return the rotation angle of the image.

        The angle is defined such that a rotation angle of zero aligns north
        along the positive Y axis, and a positive rotation angle rotates north
        away from the Y axis, in the sense of a rotation from north to east.

        Note that the rotation angle is defined in a flat map-projection of the
        sky. It is what would be seen if the pixels of the image were drawn
        with their pixel widths scaled by the angular pixel increments returned
        by the get_axis_increments() method.

        Parameters
        ----------
        unit : `astropy.units.Unit`
            The unit to give the returned angle (degrees by default).

        Returns
        -------
        out : float
            The angle between celestial north and the Y axis of
            the image, in the sense of an eastward rotation of
            celestial north from the Y-axis.

        """
        cd = get_cd(header_or_wcs)
        return image_angle_from_cd(cd, unit)

def get_saturate(fits_header):
    """
    Return the value of the MAXLIN keyword in the header.

    If the MAXLIN keyword is not present (or it is equal to 0.0),
    return the SATURATE keyword instead. If neither are present,
    return a default value.
    """

    default_satlev = 65535
    try:
        satlev = fits_header.get('MAXLIN', 0.0)
        if satlev <= 0.0 or satlev == 'N/A':
            raise KeyError
    except KeyError:
            satlev = fits_header.get('SATURATE', default_satlev)
            if satlev == default_satlev:
                logger.warning(f"SATURATE missing, default of {default_satlev} assumed")
            elif satlev <= 0.0:
                 satlev = default_satlev
                 logger.warning(f"SATURATE bad, default of {default_satlev} assumed")
            else:
                satlev = int(satlev * 0.9)

    return satlev

def create_weight_image(fits_file):

    """ Create a weight image for SWarp from the bad pixel mask (BPM) HDU
    of the original fits file, and the rms image generated by SExtractor. """

    if not os.path.exists(fits_file):
        logger.error("FITS file %s does not exist" % fits_file)
        return -11
    try:
        hdulist = fits.open(fits_file)
    except IOError as e:
        logger.error("Unable to open FITS image %s (Reason=%s)" % (fits_file, e))
        return -12

    # SCI HDU
    try:
        scidata = hdulist['SCI'].data
        sciheader = hdulist['SCI'].header
    except KeyError:
        logger.error("SCI HDU not found in %s." % fits_file)
        return -13

    # BPM HDU
    try:
        maskdata = hdulist['BPM'].data
    except KeyError as e:
        logger.error("BPM HDU not found in %s" % fits_file)
        return -14

    # RMS image
    if fits_file.endswith(".fz"):
        rms_file = fits_file.replace(".fits.fz", ".rms.fits")
    else:
        rms_file = fits_file.replace(".fits", ".rms.fits")
    if rms_file == fits_file:
        # We don't want to use the science data as rms data!
        logger.error("%s is a FITS file, but does not end in .fits or .fits.fz" % fits_file)
        return -15
    if not os.path.exists(rms_file):
        logger.error("RMS file %s does not exist" % rms_file)
        return -16
    try:
        rms_hdulist = fits.open(rms_file)
        if len(rms_hdulist) != 1:
            logger.error("Unexpected number of HDUs in RMS image")
            return -18
        rmsdata = rms_hdulist[0].data
    except IOError as e:
        logger.error("Unable to open RMS image %s (Reason=%s)" % (rms_file, e))
        return -17

    # Create boolean array based on mask
    boolean_mask = np.array(maskdata, dtype=bool)

    # Create an array to hold the weight values
    weightdata = np.empty_like(maskdata, dtype='<f4')
    weightdata[~boolean_mask] = 1 / rmsdata[~boolean_mask] ** 2
    weightdata[boolean_mask] = 0.

    # Additional mask based on saturation value
    max_satur = get_saturate(sciheader)
    satur_ind = scidata >= max_satur
    weightdata[satur_ind] = 0.

    # Create new weights FITS file
    del(sciheader['EXTNAME'])
    sciheader['L1FRMTYP'] = ('WEIGHT', 'Type of processed image')

    if fits_file.endswith(".fits.fz"):
        weight_file = fits_file.replace(".fits.fz", ".weights.fits")
    else:
        weight_file = fits_file.replace(".fits", ".weights.fits")
    if weight_file == fits_file:
        # We don't want to overwrite the original file!
        logger.error("%s is a FITS file, but does not end in .fits or .fits.fz" % fits_file)
        return -15

    hdu = fits.PrimaryHDU(weightdata, sciheader)
    weight_hdulist = fits.HDUList(hdu)
    weight_hdulist.writeto(weight_file, overwrite = True, checksum = True)

    hdulist.close()
    rms_hdulist.close()

    return weight_file

def create_rms_image(fits_file):

    """ Create an aligned rms image for Hotpants from the aligned weight image generated by SWarp. """

    if not os.path.exists(fits_file):
        logger.error("FITS file %s does not exist" % fits_file)
        return -11
    try:
        hdulist = fits.open(fits_file)
    except IOError as e:
        logger.error("Unable to open FITS image %s (Reason=%s)" % (fits_file, e))
        return -12

    # Main image
    scidata = hdulist[0].data
    sciheader = hdulist[0].header

    # Weight image
    weight_file = fits_file.replace(".fits", ".weight.fits")
    if weight_file == fits_file:
        # We don't want to use the science data as weight data!
        logger.error("%s is a FITS file, but does not end in .fits" % fits_file)
        return -15
    if not os.path.exists(weight_file):
        logger.error("Weight file %s does not exist" % weight_file)
        return -16
    try:
        weight_hdulist = fits.open(weight_file)
        if len(weight_hdulist) != 1:
            logger.error("Unexpected number of HDUs in weight image")
            return -18
        weightdata = weight_hdulist[0].data
    except IOError as e:
        logger.error("Unable to open weight image %s (Reason=%s)" % (weight_file, e))
        return -17

    # Create an array to hold the rms values
    rmsdata = np.empty_like(scidata, dtype='<f4')
    rmsdata = 1 / np.sqrt(weightdata)

    # Mask based on saturation value
    max_satur = get_saturate(sciheader)
    satur_ind = scidata >= max_satur
    rmsdata[satur_ind] = np.sqrt(50000.)

    # Create new rms FITS file
    sciheader['L1FRMTYP'] = ('RMS', 'Type of processed image')

    rms_file = fits_file.replace(".fits", ".rms.fits")
    if rms_file == fits_file:
        # We don't want to overwrite the original file!
        logger.error("%s is a FITS file, but does not end in .fits" % fits_file)
        return -15

    hdu = fits.PrimaryHDU(rmsdata, sciheader)
    rms_hdulist = fits.HDUList(hdu)
    rms_hdulist.writeto(rms_file, overwrite = True, checksum = True)

    hdulist.close()
    weight_hdulist.close()

    return rms_file

def get_reference_name(field_ra, field_dec, site, instrument, obs_filter, obs_date=None):
    """ Create a name for a co-added reference image based on
    the site, instrument, filter, RA and Dec. Also optionally [obs_date]
    can be passed (as either a str or a datetime) and it will be included
    in the filename after the coordinates"""

    if not isinstance(field_ra, float) or not isinstance(field_dec, float):
        logger.error("Passed RA or Dec is not a floating point.")
        return -1

    try:
        site_str = site.lower()
    except AttributeError:
        logger.error("Passed Site is not a string.")
        return -99
    try:
        instrument_str = instrument.lower()
    except AttributeError:
        logger.error("Passed Instrument is not a string.")
        return -99
    date_str = ''
    if obs_date:
        try:
            date_str = '_' + obs_date.strftime("%Y%m%d")
        except AttributeError:
            try:
                date_str = '_' + obs_date.replace('-', '').replace('/', '')[0:8]
            except (TypeError, AttributeError):
                logger.error("Couldn't parse obs_date")
                return -98
    outname = f"reference_{site_str}_{instrument_str}_{obs_filter}_{field_ra:06.2f}_{field_dec:+06.2f}{date_str}.fits"

    return outname

def find_reference_images(ref_dir, match):
    """ Find all of the existing reference images in the specified folder
    that match the given format. """
    pattern = os.path.join(ref_dir, match)

    ref_frames = glob(pattern)
    return ref_frames

def determine_reffield_for_block(obs_block, dbg=False):
    """Determines the reference field for the passed <obs_block>"""
    field = None
    if obs_block.calibsource is not None and obs_block.calibsource.source_type == StaticSource.REFERENCE_FIELD:
        field = obs_block.calibsource
    else:
        if dbg: print("Finding nearest reference field")
        frames = Frame.objects.filter(block=obs_block, frametype=Frame.NEOX_RED_FRAMETYPE, rms_of_fit__gt=0).order_by('midpoint')
        num_frames = frames.count()
        if num_frames > 0:
            midframe_index = int(num_frames / 2)
            frame = frames[midframe_index]
            if dbg: print(frame, frame.wcs)
            ra,dec = frame.wcs.all_pix2world(frame.get_x_size() / 2, frame.get_y_size() / 2, 0)
            obspos_start = SkyCoord(ra, dec,unit='deg')
            ref_fields = StaticSource.objects.filter(source_type=StaticSource.REFERENCE_FIELD, quality__gte=0)
            min_sep = 180*u.deg
            for ref_field in ref_fields.order_by('id'):
                pos = SkyCoord(ref_field.ra, ref_field.dec, unit='deg')
                sep = obspos_start.separation(pos)
                if sep < min_sep:
                    min_sep = sep
                    field = ref_field
                if dbg: print(f"{ref_field.name}: {pos.ra.deg:.3f} {pos.dec.deg:+.3f}  Sep= {sep.to(u.arcmin):.2f}")
            if dbg: print("Best field", field)
    return field

def determine_reference_frame_for_block(obs_block, reference_dir, obs_filter=None, dbg=False):
    """Find the reference frame in <reference_dir> for <obs_block> with optional [obs_filter]
    Returns the filepath to the reference frame (or None if not found).
    """
    ref_name = None
    
    field = determine_reffield_for_block(obs_block)
    if dbg: print(field)
    if field is not None:
        frames = Frame.objects.filter(block=obs_block, frametype=Frame.NEOX_RED_FRAMETYPE, rms_of_fit__gte=0)
        if dbg: print(f"# of unfiltered frames= {frames.count()}")
        if obs_filter is not None:
            filtered_frames = frames.filter(filter=obs_filter)
        else:
            filtered_frames = frames
            obs_filters = frames.order_by('filter').values_list("filter", flat=True).distinct()
            if obs_filters.count() > 1:
                obs_filter = '[' + ",".join(obs_filters) + ']'
            obs_filter = obs_filters[0]

        if dbg: print(f"# of   filtered frames= {filtered_frames.count()}")
        if filtered_frames.count() > 0:
            # Find all existing reference frames
            ref_frames = find_reference_images(reference_dir, "reference*.fits")
            if dbg: print("Found", len(ref_frames), " reference frames. Ref frames:\n", ref_frames)
            # Check if existing reference frame exists
            ref_frame_name = get_reference_name(field.ra, field.dec, obs_block.site, filtered_frames[0].instrument, obs_filter, '*')
            if dbg: print(ref_frame_name)
            #match_ref_frames = [frame for frame in ref_frames if os.path.basename(frame)==ref_frame_name]
            ref_names = find_reference_images(reference_dir, ref_frame_name)
            ### XXX Replace with finding best FWHM version
            if len(ref_names) >= 1:
                ref_name = ref_names[0]
        else:
            print("No matching frames found")
    return ref_name

def get_fits_imagestats(fits_filename, keyword, center = None, size = None):
    """Finds std, median, or mean of pixel data in FITS image referenced <fits_filename>, depending 
    on \<keyword\>. Pixel data will optionally be cropped to a specified \<size\> 
    (x, y) around a specified \<center\> (x, y)"""
    if fits_filename is None:
        return None
    if os.path.exists(fits_filename) is False:
        return None
    data = fits.getdata(fits_filename)
    if center is not None and size is not None:
        y_lower = center[1] - (size[1]/2)
        y_upper = center[1] + (size[1]/2)
        x_lower = center[0] - (size[0]/2)
        x_upper = center[0] + (size[0]/2)
        stats = sigma_clipped_stats(data[(int(y_lower)):(int(y_upper)), (int(x_lower)):(int(x_upper))], sigma = 3, maxiters = 5)
    else:
        stats = sigma_clipped_stats(data, sigma = 3, maxiters = 5)
    if keyword == "std":
        return stats[2]
    if keyword == 'median':
        return stats[1]
    if keyword == "mean":
        return stats[0]
