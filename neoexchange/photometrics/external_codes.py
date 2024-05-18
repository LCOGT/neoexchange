"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2016-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

import logging
import os
import re
from math import floor
from datetime import datetime, timedelta

from subprocess import call, PIPE, Popen, TimeoutExpired
from collections import OrderedDict
import warnings
from shutil import unpack_archive
from glob import glob

from astropy.io import fits
from astropy.io.votable import parse
from astropy.wcs import WCS, FITSFixedWarning, InvalidTransformError
from astropy.wcs.utils import proj_plane_pixel_scales
from numpy import loadtxt, split, empty, median, absolute, sqrt, ceil

from core.models import detections_array_dtypes
from core.utils import NeoException
from astrometrics.time_subs import timeit
from photometrics.catalog_subs import oracdr_catalog_mapping, banzai_catalog_mapping, \
    banzai_ldac_catalog_mapping, fits_ldac_to_header, open_fits_catalog
from photometrics.image_subs import create_weight_image, create_rms_image, get_saturate, get_rot

logger = logging.getLogger(__name__)


#
#
# DEFAULT CONFIG FUNCTIONS
#
#


def default_mtdlink_config_files():
    """Return a list of the needed files for MTDLINK. The config file should be in
    element 0"""

    config_files = ['mtdi.lcogt.param']

    return config_files


def default_scamp_config_files():
    """Return a list of the needed files for SCAMP. The config file should be in
    element 0"""

    config_files = ['scamp_neox_gaiadr2.cfg']

    return config_files


def default_sextractor_config_files(catalog_type='ASCII'):
    """Return a list of the needed files for SExtractor. The config file should
    be in element 0"""

    common_config_files = ['gauss_1.5_3x3.conv', 'default.nnw']
    config_files = ['sextractor_neox.conf',
                    'sextractor_ascii.params']
    if catalog_type == 'FITS_LDAC':
        config_files = ['sextractor_neox_ldac.conf',
                        'sextractor_ldac.params']
    elif catalog_type == 'FITS_LDAC_MULTIAPER':
        config_files = ['sextractor_neox_ldac_multiaper.conf',
                        'sextractor_ldac_multiaper.params']

    config_files += common_config_files
    return config_files


def default_findorb_config_files():
    config_files = ['environ.def', 'ps_1996.dat', 'elp82.dat']
    return config_files


def default_swarp_config_files():
    """Return a list of the needed files for SWarp. The config file should
    be in element 0"""

    config_files = ['swarp_neox.conf']

    return config_files

#
#
# SETUP DIRECTORY FUNCTIONS
#
#


def setup_mtdlink_dir(source_dir, dest_dir):
    """Setup a temporary working directory for running MTDLINK in <dest_dir>. The
    needed config files are symlinked from <source_dir>"""

    mtdlink_config_files = default_mtdlink_config_files()

    return_value = setup_working_dir(source_dir, dest_dir, mtdlink_config_files)

    return return_value


def setup_scamp_dir(source_dir, dest_dir):
    """Setup a temporary working directory for running SCAMP in <dest_dir>. The
    needed config files are symlinked from <source_dir>"""

    scamp_config_files = default_scamp_config_files()

    return_value = setup_working_dir(source_dir, dest_dir, scamp_config_files)

    return return_value


def setup_sextractor_dir(source_dir, dest_dir, catalog_type='ASCII'):
    """Setup a temporary working directory for running SExtractor in <dest_dir>.
    The needed config files are symlinked from <source_dir>"""

    sextractor_config_files = default_sextractor_config_files(catalog_type)

    return_value = setup_working_dir(source_dir, dest_dir, sextractor_config_files)

    return return_value


def setup_hotpants_dir(source_dir, dest_dir):
    """Setup a temporary working directory for running HOTPANTS in <dest_dir>.
    The needed config files are symlinked from <source_dir>"""

    return_value = setup_working_dir(source_dir, dest_dir, "")

    return return_value

def setup_swarp_dir(source_dir, dest_dir):
    """Setup a temporary working directory for running SWarp in <dest_dir>.
    The needed config files are symlinked from <source_dir>"""

    swarp_config_files = default_swarp_config_files()

    return_value = setup_working_dir(source_dir, dest_dir, swarp_config_files)

    return return_value


def setup_findorb_dir(source_dir, dest_dir):
    """Setup things for running find_orb. Currently a no-op (apart from the
    directory creation)"""

    findorb_config_files = default_findorb_config_files()

    return_value = setup_working_dir(source_dir, dest_dir, findorb_config_files)

    return return_value


def setup_findorb_environ_file(source_dir, site_code=500, start_time=datetime.utcnow()):
    """Copies the initial environ.def file in <source_dir> to environ.dat, also
    in <source_dir>. The EPHEM_START and EPHEM_MPC_CODE are altered as they are
    read in and set to the [start_time] and [site_code] respectively"""

    environ_orig = os.path.join(source_dir, 'environ.def')
    environ_new = os.path.join(source_dir, 'environ.dat')

    in_fh = open(environ_orig, 'r')
    lines = in_fh.readlines()
    in_fh.close()

    with open(environ_new, 'w') as out_fh:
        for line in lines:
            if line.lstrip()[0:11] == 'EPHEM_START':
                line = "EPHEM_START={}".format(start_time.strftime("%Y-%m-%d %H:%M"))
            elif line.lstrip()[0:14] == 'EPHEM_MPC_CODE':
                line = "EPHEM_MPC_CODE=1 {:3s}".format(str(site_code).upper())
            elif line.lstrip()[0:11] == 'EPHEM_STEPS':
                line = "EPHEM_STEPS=24 30m"
            elif line.lstrip()[0:9] == 'SETTINGS=':
                line = 'SETTINGS=N,4,5,65568,2.000000,1.000000'
            print(line.rstrip(), file=out_fh)

    return


def setup_working_dir(source_dir, dest_dir, config_files):
    """Sets up a temporary working directory for running programs in <dest_dir>.
    The temporary working directory is created if needed and the required config
    files (given in a list in <config_files>) are symlinked from <source_dir> if
    they don't already exist in <dest_dir>"""

    source_dir = os.path.abspath(source_dir)
    if not os.path.exists(source_dir):
        logger.error("Source path '%s' does not exist" % source_dir)
        return -1

    if not os.path.exists(dest_dir):
        try:
            oldumask = os.umask(0o002)
            os.makedirs(dest_dir)
            os.umask(oldumask)
        except OSError:
            logger.error("Destination path '%s' could not be created" % dest_dir)
            return -2

    num_bad_links = 0
    for config in config_files:
        config_src_filepath = os.path.join(source_dir, config)
        config_dest_filepath = os.path.join(dest_dir, config)
        if os.path.lexists(config_dest_filepath):
            try:
                os.unlink(config_dest_filepath)
            except OSError:
                logger.warning("Could not unlink %s" % config_dest_filepath)
        try:
            os.symlink(config_src_filepath, config_dest_filepath)
        except OSError:
            logger.error("Could not create link for %s to %s" % ( config, config_dest_filepath))
            num_bad_links += 1
    return_status = 0
    if num_bad_links > 0:
        return_status = -3
    return return_status


#
#
# DETERMINE OPTIONS FUNCTIONS
#
#


def determine_sextractor_options(fits_file, dest_dir, checkimage_type=[], catalog_type='FITS_LDAC'):
    """Determines and returns the SExtractor command line options string to use (which
    override the deafults in the SExtractor config file) for FITS image file <fits_fits>
    The following options are determined from the FITS file based on a header
    mapping:
    * -GAIN: FITS GAIN keyword
    * -PIXEL_SCALE: Mean pixel scale from the WCS
    * -SATUR_LEVEL: FITS MAXLIN keyword if present and good, otherwise SATURATE
    [checkimage_type] can be 0 to 2 of 'BACKGROUND_RMS' and '-BACKGROUND' to
    turn on output of the RMS or a background-subtracted image respectively.
    """

    # Mapping keys in the generalized headers that NEOX uses to SExtractor
    # command line options
    option_mapping = OrderedDict([
                        ('gain'      , '-GAIN'),
                        ('pixel_scale' , '-PIXEL_SCALE'),
                        ('saturation'  , '-SATUR_LEVEL'),
                     ])

    options = ''

    try:
        hdulist = fits.open(fits_file)
    except IOError as e:
        logger.error(f"Unable to open FITS image {fits_file} (Reason={e})")
        return options

    header = hdulist[0].header
    # Suppress warnings from newer astropy versions which raise
    # FITSFixedWarning on the lack of OBSGEO-L,-B,-H keywords even
    # though we have OBSGEO-X,-Y,-Z as recommended by the FITS
    # Paper VII standard...
    warnings.simplefilter('ignore', category=FITSFixedWarning)
    try:
        fits_wcs = WCS(header)
    except InvalidTransformError:
        raise NeoException('Invalid WCS solution')

    header_mapping, table_mapping = banzai_catalog_mapping()

    for option in option_mapping.keys():
        keyword = header_mapping[option]
        if keyword == '<MAXLIN>':
            value = get_saturate(header)
        elif keyword == '<WCS>':
            pixscale = proj_plane_pixel_scales(fits_wcs).mean()*3600.0
            value = round(pixscale, 5)
        else:
            value = header.get(keyword, -99)
        if value != -99:
            options += option_mapping[option] + ' ' + str(value) + ' '
    options = options.rstrip()

    # Add output catalog file name
    output_catalog = os.path.basename(fits_file)
    extension = '_ldac.fits'
    if catalog_type.startswith('ASCII'):
        extension = '.cat'
    output_catalog = output_catalog.replace('[SCI]', '').replace('.fits', extension)
    output_catalog = os.path.join(dest_dir, output_catalog)
    options += f' -CATALOG_NAME {output_catalog}'

    # SWarp requires an rms image later in the pipeline.
    # Hotpants requires a background-subtracted image later in the pipeline.
    if len(checkimage_type) > 0:

        checkimage_name = [None] * len(checkimage_type)

        if 'BACKGROUND_RMS' in checkimage_type:
            i = checkimage_type.index('BACKGROUND_RMS')
            checkimage_name[i] = os.path.join(dest_dir, os.path.basename(fits_file.replace(".fits", ".rms.fits")))

        # Background map
        if 'BACKGROUND' in checkimage_type:
            i = checkimage_type.index('BACKGROUND')
            checkimage_name[i] = os.path.join(dest_dir, os.path.basename(fits_file.replace(".fits", ".bkgd.fits")))

        # Background subtracted image
        if '-BACKGROUND' in checkimage_type:
            i = checkimage_type.index('-BACKGROUND')
            checkimage_name[i] = os.path.join(dest_dir, os.path.basename(fits_file.replace(".fits", ".bkgsub.fits")))

        if 'APERTURES' in checkimage_type:
            i = checkimage_type.index('APERTURES')
            checkimage_name[i] = os.path.join(dest_dir, os.path.basename(fits_file.replace(".fits", ".apers.fits")))

        if None in checkimage_name:
            logger.error("At least one checkimage_type you have entered is not supported by NEOX.")
            return -6

        checkimage_type_str = ','.join(checkimage_type)
        checkimage_name_str = ','.join(checkimage_name)
        options += f' -CHECKIMAGE_TYPE {checkimage_type_str} -CHECKIMAGE_NAME {checkimage_name_str}'

    if max(header['naxis1'], header['naxis2']) < 2100:
        options += ' -BACK_SIZE 32'
    else:
        options += ' -BACK_SIZE 64'

    hdulist.close()
    return options


def determine_hotpants_options(ref, sci, source_dir, dest_dir, dbgOptions=False):
    """
    Run SExtractor on <sci> image to subtract the background,
    then align the <ref> using SWarp.

    https://github.com/acbecker/hotpants

    Required options are:
    [-inim fitsfile]  : comparison image to be differenced
    [-tmplim fitsfile]: template image
    [-outim fitsfile] : output difference image
    """
    # Check to make sure required images exist
    if not os.path.exists(ref):
        logger.error(f"{ref} not found.")
        return -4
    elif not os.path.exists(sci):
        logger.error(f"{sci} not found.")
        return -5

    ref_rms = os.path.join(dest_dir, os.path.basename(ref).replace(".fits", ".rms.fits"))

    if not os.path.exists(ref_rms):
        logger.error(f"{ref_rms} not found.")
        return -6

    if dbgOptions:
        # Normally this is already run as part of the larger pipeline
        run_sextractor(source_dir, dest_dir, sci + '[SCI]', checkimage_type=['BACKGROUND_RMS', '-BACKGROUND'], catalog_type='FITS_LDAC')

    sci_rms = os.path.join(dest_dir, os.path.basename(sci).replace(".fits", ".rms.fits"))
    sci_bkgsub = os.path.join(dest_dir, os.path.basename(sci).replace(".fits", ".bkgsub.fits"))

    if not os.path.exists(sci_rms):
        logger.error(f"{sci_rms} not found.")
        return -7
    if not os.path.exists(sci_bkgsub):
        logger.error(f"{sci_bkgsub} not found.")
        return -8

    aligned_ref = align_to_sci(ref, sci, source_dir, dest_dir)
    aligned_rms = align_to_sci(ref_rms, sci_rms, source_dir, dest_dir)

    if type(aligned_ref) != str or type(aligned_rms) != str:
        logger.error(f"Error occurred in SWarp while aligning images.")
        return -9

    output_diff_image = os.path.join(dest_dir, os.path.basename(sci).replace('.fits', '.subtracted.fits'))
    output_noise_image = output_diff_image.replace('.fits', '.rms.fits')

    # Get the relevant header and data information
    with fits.open(sci_bkgsub) as sci_hdulist:
        try:
            sci_header = sci_hdulist['SCI'].header
            sci_bkgsub_data = sci_hdulist['SCI'].data
        except KeyError:
            sci_header = sci_hdulist[0].header
            sci_bkgsub_data = sci_hdulist[0].data

    ref_data = fits.getdata(ref)

    satlev = get_saturate(sci_header)
    satlev = round(satlev, 0)

    scibkg = median(sci_bkgsub_data)
    scibkgstd = 1.4826 * median(absolute(sci_bkgsub_data - scibkg))
    refbkg = median(ref_data)
    refbkgstd =1.4826 * median(absolute(ref_data - refbkg))
    il = scibkg - 10 * scibkgstd    #lower valid data count, template (0)
    tl = refbkg - 10 * refbkgstd    #lower valid data count, image (0)

    nreg_side=3
    nrx = nreg_side    #number of image regions in x dimension (1)
    nry = nreg_side    #number of image regions in y dimension (1)
    nsx = sci_header['NAXIS1'] / 100. / nreg_side    #number of each region's stamps in x dimension (10)
    nsy = sci_header['NAXIS2'] / 100. / nreg_side    #number of each region's stamps in y dimension (10)

    sci_wcs = WCS(sci_header)
    pixscale = proj_plane_pixel_scales(sci_wcs).mean()*3600.0   #arcsec/pix
    seearcsec = sci_header['L1FWHM'] #Frame FWHM in arcsec
    seepix = seearcsec / pixscale #Convert arcsec to pixels
    r = 2.5 * seepix    #convolution kernel half width {10}
    rss = 6. * seepix   #half width substamp to extract around each centroid (15)

    fin = sqrt(50000.) #noise image only fillvalue (0.0e+00)

    options = f'-inim {sci_bkgsub} -tmplim {aligned_ref} -outim {output_diff_image} ' \
              f'-tni {aligned_rms} -ini {sci_rms} -oni {output_noise_image} ' \
              f'-hki -n i -c t -v 0 ' \
              f'-tu {satlev} -iu {satlev} ' \
              f'-tl {tl} -il {il} ' \
              f'-nrx {nrx} -nry {nry} -nsx {nsx} -nsy {nsy} ' \
              f'-r {r} -rss {rss} -fin {fin}'

    return options


def determine_swarp_align_options(ref, sci, dest_dir, outname, back_size=32, nthreads=1):

    options = ''

    weightname = outname.replace('.fits', '.weight.fits')

    if 'mask' in sci:
        combtype = 'OR'
    else:
        combtype = 'CLIPPED'

    proj_type = 'TPV'
    if '2m0' in outname or '2m0' in sci:
        proj_type = 'TAN'

    options = f'-BACK_SIZE {back_size} ' \
              f'-IMAGEOUT_NAME {outname} ' \
              f'-NTHREADS {nthreads} ' \
              f'-VMEM_DIR {dest_dir} ' \
              f'-RESAMPLE_DIR {dest_dir} ' \
              f'-SUBTRACT_BACK N ' \
              f'-WEIGHTOUT_NAME {weightname} ' \
              f'-WEIGHT_TYPE NONE ' \
              f'-COMBINE_TYPE {combtype} ' \
              f'-PROJECTION_TYPE {proj_type} '

    return options

def make_ref_head(ref, sci, dest_dir, outname):
    """
    Create a new .head file in <dest_dir> containing the NAXIS and WCS data from the <sci> image.
    """

    # Sci image header
    with fits.open(sci) as sci_hdulist:
        try:
            align_header = sci_hdulist['SCI'].header
        except KeyError:
            align_header = sci_hdulist[0].header

    # Only the WCS data in the header
    head = WCS(align_header).to_header(relax=True)

    headpath = outname.replace('.fits', '.head')
    with open(headpath, 'w') as f:

        # Write the NAXIS data to the head file
        for card in align_header.cards:
            if card.keyword.startswith('NAXIS'):
                f.write(f'{card.image}\n')

        # Write the WCS data to the head file
        for card in head.cards:
            f.write(f'{card.image}\n')

    return headpath

def determine_swarp_options(inweight, outname, dest_dir, back_size=32):
    """
    Takes weight.in filename
    If there are problems with this list, they should already be caught in run_swarp().
    """

    options = ''

    wgtout = outname.replace('.fits', '.weight.fits')

    proj_type = 'TPV'
    if '2m0' in outname or '2m0' in inweight or \
        'coj_ep' in outname or 'coj_ep' in inweight or \
        'ogg_ep' in outname or 'ogg_ep' in inweight:
        proj_type = 'TAN'

    options = f'-BACK_SIZE {back_size} ' \
              f'-IMAGEOUT_NAME {outname} ' \
              f'-VMEM_DIR {dest_dir} ' \
              f'-RESAMPLE_DIR {dest_dir} ' \
              f'-WEIGHT_IMAGE @{inweight} ' \
              f'-WEIGHTOUT_NAME {wgtout} ' \
              f'-PROJECTION_TYPE {proj_type} '
    return options


def make_file_list(images, output_file_name):
    """
    Takes a list of images and saves them to a new text file in the specified path.
    The list contains strings of the full pathway to each file.

    The list can be created by using the following as an example:
        data_root = os.path.join(os.getenv('HOME'), 'data','lco','')
        fits_files = glob(data_root + 'lsc*e91.fits.fz')
    """
    #This also overwrites any existing file of the same name
    with open(output_file_name, 'w') as f:
        for image in images:
            f.write(f"{image}\n")

    return output_file_name


def normalize(images, swarp_zp_key="L1ZP"):
    """
    Normalize all images to the same zeropoint by adding FLXSCALE and FLXSCLZP to their headers.
    This uses the FITS header keyword given by [swarp_zp_key] (defaults to `L1ZP`)
    """

    bad_file_count = 0

    for image in images:
        hdulist = fits.open(image)
        try:
            sci_index = hdulist.index_of('SCI')
        except KeyError:
            sci_index = 0
        im_header = hdulist[sci_index].header
        if swarp_zp_key in im_header:
            fluxscale = 10**(-0.4 * (im_header[swarp_zp_key] - 25.))
            im_header['FLXSCALE'] = (fluxscale, 'Flux scale factor for coadd')
            im_header['FLXSCLZP'] = (25.0, 'FLXSCALE equivalent ZP')
            hdulist.writeto(image, overwrite=True, checksum=True)
        else:
            logger.error(f"Keyword {swarp_zp_key} not present in {image}. Image could not be normalized, default flux scale value is 1.0")
            bad_file_count += 1
        hdulist.close()

    return_code = 0
    if bad_file_count > 0:
        return_code = -6

    return return_code

def round_up_to_odd(f):
    """Rounds the passed value <f> up to the nearest odd integer"""

    return int(ceil(f) // 2) * 2 + 1

def determine_astcrop_options(filename, dest_dir, xmin, xmax, ymin, ymax):
    """Determine the options for running `astcrop`. Since this is designed to
    be run in a loop over all HDUS, the string returned contains a placeholder
    '--hdu=<hdu>' that needs to be substitued.
    """

    raw_filename = os.path.basename(filename)
    output_filename = raw_filename.replace('.fits', '-trim.fits')
    output_filename = os.path.join(dest_dir, output_filename)
    # FITS files have a 1-based origin but the bounds from NumPy are/could be
    # zero-based. Ensure we don't try to start the section at 0.
    xmin = max(xmin, 1)
    ymin = max(ymin, 1)

    options = f'--mode=img --section={xmin}:{xmax},{ymin}:{ymax} --hdu=<hdu> --append --metaname=<hdu> --output={output_filename} {filename}'

    return output_filename, options

def determine_astwarp_options(filename, dest_dir, center_RA, center_DEC, width = 1991.0, height = 511.0):
    raw_filename = os.path.basename(filename)
    output_filename = os.path.join(dest_dir, raw_filename.replace('-chisel', '-crop'))
    options = f'-hINPUT-NO-SKY --center={center_RA},{center_DEC} --widthinpix --width={width},{height} --output={output_filename} {filename}'
    return output_filename, options

def determine_astarithmetic_options(filenames, dest_dir, hdu = 'ALIGNED'):
    filenames_list = " ".join(filenames)
    raw_filename = os.path.basename(filenames[0])
    if "-crop" in raw_filename:
        output_filename = os.path.join(dest_dir, raw_filename.replace("-crop", "-combine"))
    elif "-combine-superstack" in raw_filename:
        # Set output filename to middle of list
        midpoint_index = int(len(filenames) / 2)
        raw_filename = os.path.basename(filenames[midpoint_index])
        # Rip out run number from the middle if found with the regexp
        runnum_regex = r"(-\d{4})-e"
        raw_filename =  re.sub(runnum_regex, '-e', raw_filename)
        output_filename = os.path.join(dest_dir, raw_filename.replace("-combine-superstack", "-combine-hyperstack"))
    else:
        output_filename = os.path.join(dest_dir, raw_filename.replace(".fits", "-superstack.fits"))
    #original options (maybe from tutorial?)
    #options = f'--globalhdu ALIGNED --output={output_filename} {filenames_list} {len(filenames)} 5 0.2 sigclip-median'
    #values from Agata Rozek configuration/Makefile
    options = f'--globalhdu {hdu} --output={output_filename} {filenames_list} {len(filenames)} 2 0.05 sigclip-mean'
    return output_filename, options

def determine_didymos_extraction_options(filename, dest_dir, didymos_id):
    raw_filename = os.path.basename(filename)
    output_filename = os.path.join(dest_dir, raw_filename.replace('-chisel', '-didymos_chisel'))
    options = f'-hDETECTIONS {filename} {didymos_id} eq 1 erode 1 erode 1 erode --output={output_filename}'
    return output_filename, options

def determine_didymos_border_options(filename, dest_dir, didymos_id, all_borders=False):
    """Determine the options needed for astarithmetic in order to make the
    output file containing just the Didymos object detection
    contour ([all_borders=False; default]) or all objects ([all_borders=True])
    Returns the filename and command line options.
    """

    raw_filename = os.path.basename(filename)
    suffix = '-bd'
    if all_borders:
        suffix += 'a'
    output_filename = os.path.join(dest_dir, raw_filename.replace('-chisel', suffix))
    options = f'{filename} '
    if all_borders is False:
        options += f'{didymos_id} eq set-i '
    else:
        options += '0 gt set-i '
    options += f'i i 1 erode 1 erode 1 erode 0 where --output={output_filename}'
    return output_filename, options

def determine_astnoisechisel_options(filename, dest_dir, hdu = 0, bkg_only=False):
    raw_filename = os.path.basename(filename)
    output_filename = os.path.join(dest_dir, raw_filename.replace(".fits", "-chisel.fits"))
    #original options from tutorial
    # if bkg_only:
        # options = f'-h{hdu} --tilesize={tilesize} --erode={erode} --detgrowquant={detgrowquant} --detgrowmaxholesize={maxholesize} --oneelempertile --output={output_filename} {filename}'
    # else:
        # options = f'-h{hdu} --tilesize={tilesize} --erode={erode} --detgrowquant={detgrowquant} --detgrowmaxholesize={maxholesize} --output={output_filename} {filename}'
    #values from Agata Rozek configuration/Makefile
    tilesize = ''
    if 'fm2' in filename or 'coj1m011-fa12-202211' in filename:
        tilesize='--tilesize=15,15'
    if bkg_only:
        options = f'-h{hdu} --quiet {tilesize} --oneelempertile --interpnumngb=8 --minnumfalse=50 --output={output_filename} {filename}'
    else:
        options = f'-h{hdu} --quiet {tilesize} --label --rawoutput --output={output_filename} {filename}'
    return output_filename, options

def determine_image_stats(filename, hdu='SCI'):
    mean, status = run_aststatistics(filename, 'mean', hdu)
    std, status = run_aststatistics(filename, 'std', hdu)

    if mean is not None and std is not None:
        mean = float(mean)
        std = float(std)
    return mean, std

def determine_stack_astconvertt_options(filename, dest_dir, mean, std, out_type='pdf', hdu='SCI'):
    raw_filename = os.path.basename(filename)
    output_filename = os.path.join(dest_dir, raw_filename.replace(".fits", f".{out_type}"))
    #print(type(mean), type(std))
    sigrem = -0.5
    sigadd = 25

    low = mean + sigrem * std
    high = mean + sigadd * std
    #print(low,high)
    cmap = 'sls-inverse'
    #cmap = 'gray' # --invert'

    options = f'{filename} -L {low} -H {high} -h{hdu} --colormap={cmap} --output={output_filename}'
    return output_filename, options

def determine_astconvertt_options(filename, dest_dir, out_type='pdf', hdu='SCI'):
    raw_filename = os.path.basename(filename)
    output_filename = os.path.join(dest_dir, raw_filename.replace(".fits", f".{out_type}"))
    cmap = '--colormap=sls-inverse'
    #cmap = '--colormap=gray --invert'
    if '-bd' in filename:
        # Need to disable the colormap when making border images or you will
        # get identical looking images but the masking won't work properly.
        cmap = ''
        logger.debug("Disabling colormap for border images")
    options = f'{filename} -h{hdu} {cmap} --output={output_filename}'
    return output_filename, options

def determine_astmkcatalog_options(filename, dest_dir):
    raw_filename = os.path.basename(filename)
    output_filename = os.path.join(dest_dir, raw_filename.replace("-chisel", "-cat"))
    options = f'{filename} --ids --area --min-x --max-x --min-y --max-y -hDETECTIONS --output={output_filename}'
    return output_filename, options

def determine_asttable_options(filename, dest_dir):
    raw_filename = os.path.basename(filename)
    output_filename = os.path.join(dest_dir, raw_filename.replace(".fits", ".txt"))
    options = f'{filename} --output={output_filename}'
    return output_filename, options

def make_pa_rate_dict(pa, deltapa, minrate, maxrate):

    pa_rate_dict = {    'filter_pa': pa,
                        'filter_deltapa': deltapa,
                        'filter_minrate': minrate/3600.0*1440.0,  # mtdlink needs motion rates in deg/day, not arcsec/min
                        'filter_maxrate': maxrate/3600.0*1440.0,
                   }

    return pa_rate_dict


def determine_mtdlink_options(num_fits_files, param_file, pa_rate_dict):

    min_rate_str = '{:.2f}'.format(pa_rate_dict['filter_minrate'])
    max_rate_str = '{:.2f}'.format(pa_rate_dict['filter_maxrate'])

    options = ''
    options += '-paramfile' + ' ' + str(param_file) + ' '
    options += '-CPUTIME' + ' ' + str(num_fits_files*200) + ' '
    options += '-MAXMISSES' + ' ' + str(int(floor(num_fits_files/2.5))) + ' '
    options += '-FILTER_PA' + ' ' + str(pa_rate_dict['filter_pa']) + ' '
    options += '-FILTER_DELTAPA' + ' ' + str(pa_rate_dict['filter_deltapa']) + ' '
    options += '-FILTER_MINRATE' + ' ' + min_rate_str + ' '
    options += '-FILTER_MAXRATE' + ' ' + max_rate_str + ' '
    options = options.rstrip()
    return options


def determine_scamp_options(fits_catalog, external_cat_name='GAIA-DR2.cat', distort_degrees=None):
    """Assemble the command line options for SCAMP.
    Focal plane distortions are turned on by default if the filename contains
    '1m0' - this can be overridden by setting [distort_degrees].
    If [distort_degrees] is not equal to 1 (the default), then additional
    options are set to change the degree of polynomial order and switch to
    the TPV distorted tangent plane projection.
    Reference: https://fits.gsfc.nasa.gov/registry/tpvwcs/tpv.html
    """
    options = "-ASTREF_CATALOG FILE -ASTREFCAT_NAME {}".format(os.path.basename(external_cat_name))
    if ('1m0' in fits_catalog and ('-fl' in fits_catalog or '-fa' in fits_catalog)) or distort_degrees is not None:
        if distort_degrees is None:
            distort_degrees = 3
    else:
        distort_degrees = 1
    if distort_degrees != 1 and distort_degrees <= 7:
        options += " -DISTORT_DEGREES {} -PROJECTION_TYPE TPV".format(distort_degrees)
    if '2m0' in fits_catalog:
        options += " -POSANGLE_MAXERR 1 -MATCH_FLIPPED N"
    # Add unique filename-based name for the XML output file rather than 'scamp.xml'
    # which is problematic when several versions are running in parallel.
    xml_file = os.path.splitext(os.path.basename(fits_catalog))[0] + '.xml'
    if os.path.basename(fits_catalog) == xml_file:
        logger.warning("Trying to create XML output file with the same name as input FITS catalog. Resetting to scamp.xml")
        xml_file = 'scamp.xml'

    options += " -XML_NAME {}".format(xml_file)

    return options


def determine_findorb_options(site_code, start_time=datetime.utcnow()):
    """Options for find_orb:
    -z: use config directory for files (in $HOME/.find_orb),
    -c combine designations,
    -q: quiet,
    -C <site_code>: set MPC site code for ephemeris to <site_code>,
    -e new.ephem: output ephemeris to new.ephem,
    -tE<date>: use <date> as the epoch of elements (rounded up to nearest day)
    """

    epoch_date = start_time.date() + timedelta(days=1)

    options = "-z -c -q -C {} -tE{}".format(site_code, epoch_date.strftime("%Y-%m-%d"))

    return options


#
#
# RUN FUNCTIONS
#
#


def find_binary(program):
    """Python equivalent of 'which' command to find a binary in the path (can
    also be given a specific pathname"""

    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None


def add_l1filter(fits_file):
    """Adds a L1FILTER keyword into the <fits_file> with the same value
    as FILTER. If not found, nothing is done."""

    try:
        hdulist = fits.open(fits_file, mode='update')
    except:# IOError as e:
        logger.error(f"Unable to open FITS image {fits_file} (Reason={e})")
        return -99

    prihdr = hdulist[0].header
    filter_val = prihdr.get('FILTER', None)
    if filter_val:
        prihdr['L1FILTER'] = (filter_val, 'Copy of FILTER for SCAMP')
    hdulist.close()

    return 0


@timeit
def run_sextractor(source_dir, dest_dir, fits_file, checkimage_type=[], binary=None, catalog_type='FITS_LDAC', dbg=False):
    """Run SExtractor (using either the binary specified by [binary] or by
    looking for 'sex' in the PATH) on the passed <fits_file> with the results
    and any temporary files created in <dest_dir>. <source_dir> is the path
    to the required config files."""

    status = setup_sextractor_dir(source_dir, dest_dir, catalog_type)
    if status != 0:
        return status

    binary = binary or find_binary("sex")
    if binary is None:
        logger.error("Could not locate 'sex' executable in PATH")
        return -42

    root_fits_file = fits_file
    if '[SCI]' in fits_file:
        # Banzai format, strip off extension
        root_fits_file = fits_file.replace('[SCI]', '')

    if not os.path.exists(root_fits_file):
        logger.error(f"{root_fits_file} not found.")
        return -4
    if not root_fits_file.endswith(".fits"):
        logger.error(f"{root_fits_file} does not end with .fits")
        return -5

    # If we are making FITS_LDAC catalogs for SCAMP, we need to create a new
    # header keyword of L1FILTER and set the value to FILTER. This prevents
    # SCAMP false matching on the first FITS keyword starting with FILTER
    if catalog_type == 'FITS_LDAC' or catalog_type == 'FITS_LDAC_MULTIAPER':

        status = add_l1filter(root_fits_file)
        if status != 0:
            return status

    sextractor_config_file = default_sextractor_config_files(catalog_type)[0]
    if '[SCI]' in fits_file:
        options = determine_sextractor_options(root_fits_file, dest_dir, checkimage_type, catalog_type)
    else:
        options = determine_sextractor_options(fits_file, dest_dir, checkimage_type, catalog_type)

    cmdline = "%s %s -c %s %s" % ( binary, fits_file, sextractor_config_file, options )
    cmdline = cmdline.rstrip()

    if dbg is True:
        retcode_or_cmdline = cmdline
    else:
        # This executes the command to the terminal
        logger.debug("cmdline=%s" % cmdline)
        args = cmdline.split()
        retcode_or_cmdline = call(args, cwd=dest_dir)

    return retcode_or_cmdline

@timeit
def run_swarp(source_dir, dest_dir, images, outname='reference.fits', binary=None, swarp_zp_key='L1ZP', dbg=False):
    """Run SWarp (using either the binary specified by [binary] or by
    looking for 'swarp' in the PATH) on the passed <images> with the
    results (written to [outname]; defaults to `reference.fits`)
    and any temporary files created in <dest_dir>. <source_dir> is the
    path to the required config files.
    The passed <images> list should NOT include [SCI] extensions."""

    status = setup_swarp_dir(source_dir, dest_dir)
    if status != 0:
        return status

    binary = binary or find_binary("swarp")
    if binary is None:
        logger.error("Could not locate 'swarp' executable in PATH")
        return -42

    swarp_config_file = default_swarp_config_files()[0]

    # Symlink images and weights to dest_dir and create lists of these links
    linked_images = []
    linked_weights = []
    fwhms = []
    for image in images:
        if os.path.exists(image):
            image_filename = os.path.basename(image)
            image_newfilepath = os.path.join(dest_dir, image_filename)
            if os.path.exists(image_newfilepath) is False:
                os.symlink(image, image_newfilepath)
            linked_images.append(image_filename + '[SCI]')
            try:
                fwhm = fits.getval(image_newfilepath, 'L1FWHM')
            except KeyError:
                fwhm = None
            if fwhm and fwhm > 0:
                fwhms.append(fwhm)
        else:
            logger.error(f'Could not find {image}')
            return -3

        if image.endswith(".fits.fz"):
            weight_image = image.replace(".fits.fz", ".weights.fits")
        else:
            weight_image = image.replace(".fits", ".weights.fits")
        if weight_image == image:
            logger.error("'%s' does not end in .fits or .fits.fz" % image)
            return -5

        weight_filename = os.path.basename(weight_image)
        weight_newfilepath = os.path.join(dest_dir, weight_filename)

        # If the weight image doesn't exist, make one! (in dest_dir)
        if os.path.exists(weight_newfilepath) is False:
            weight_status = create_weight_image(image_newfilepath)
            if type(weight_status) != str:
                logger.error("Error occured in create_weight_image()")
                return weight_status
        linked_weights.append(weight_filename)

    inlist = make_file_list(linked_images, os.path.join(dest_dir, 'images.in'))
    inweight = make_file_list(linked_weights, os.path.join(dest_dir, 'weight.in'))
    # Compute min, max and median FWHM
    min_fwhm = max_fwhm = median_fwhm = -99
    if len(fwhms) >= 1:
        min_fwhm = min(fwhms)
        max_fwhm = max(fwhms)
        median_fwhm = median(fwhms)
    keyword_mapping = { 'FWHMMIN'  : (min_fwhm, 'Minimum FWHM in the stack'),
                        'FWHMMAX'  : (max_fwhm, 'Maximum FWHM in the stack'),
                        'FWHMMDIN' : (median_fwhm, 'Median FWHM in the stack')
                      }
    normalize_status = normalize(images, swarp_zp_key)
    if normalize_status != 0:
        return normalize_status

    options = determine_swarp_options(inweight, outname, dest_dir)

    #assemble command line
    cmdline = "%s -c %s @%s %s" % (binary, swarp_config_file, inlist, options )
    cmdline = cmdline.rstrip()

    #run swarp
    if dbg is True:
        retcode_or_cmdline = cmdline
    else:
        # This executes the command to the terminal
        logger.debug("cmdline=%s" % cmdline)
        args = cmdline.split()
        retcode_or_cmdline = call(args, cwd=dest_dir)
        if retcode_or_cmdline == 0:
            out_filepath = os.path.join(dest_dir, outname)
            with fits.open(out_filepath, mode='update') as hdul:
                header = hdul[0].header
                prior_keyword = 'COMBINET'
                for keyword, values in keyword_mapping.items():
                    header.remove(keyword, ignore_missing=True, remove_all=False)
                    header.insert(prior_keyword, (keyword, values[0], values[1]), after=True)
                    prior_keyword = keyword

                hdul.flush()

    #convert output weight to rms
    if not dbg:
        outname_newfilepath = os.path.join(dest_dir, outname)
        rms_status = create_rms_image(outname_newfilepath)
        if type(rms_status) != str:
            logger.error("Error occured in create_rms_image()")
            return rms_status
        else:
            with fits.open(rms_status, mode='update') as hdul:
                header = hdul[0].header
                prior_keyword = 'COMBINET'
                for keyword, values in keyword_mapping.items():
                    header.remove(keyword, ignore_missing=True, remove_all=False)
                    header.insert(prior_keyword, (keyword, values[0], values[1]), after=True)
                    prior_keyword = keyword

                hdul.flush()

    return retcode_or_cmdline

@timeit
def run_hotpants(ref, sci, source_dir, dest_dir, binary=None, dbg=False, dbgOptions=False):
    """Run HOTPANTS (using either the binary specified by [binary] or by
    looking for 'hotpants' in the PATH) on the passed <ref> and <sci> images with the
    results and any temporary files created in <dest_dir>. <source_dir> is the
    path to the required config files."""

    status = setup_hotpants_dir(source_dir, dest_dir)
    if status != 0:
        return status

    binary = binary or find_binary("hotpants")
    if binary is None:
        logger.error("Could not locate 'hotpants' executable in PATH")
        return -42

    options = determine_hotpants_options(ref, sci, source_dir, dest_dir, dbgOptions=dbgOptions)
    if type(options) != str:
        return options

    #assemble command line
    cmdline = "%s %s" % (binary, options)
    cmdline = cmdline.rstrip()

    #run hotpants
    if dbg is True:
        retcode_or_cmdline = cmdline
    else:
        # This executes the command to the terminal
        logger.debug("cmdline=%s" % cmdline)
        args = cmdline.split()

        # Open /dev/null for writing to lose the Hotpants output into
        print(f"\nHotpants started.\nSubtracting {ref} from {sci}...\n")
        DEVNULL = open(os.devnull, 'w')
        retcode_or_cmdline = call(args, cwd=dest_dir, stdout=DEVNULL, stderr=DEVNULL)
        DEVNULL.close()

    return retcode_or_cmdline

def align_to_sci(ref, sci, source_dir, dest_dir):
    """Resamples and aligns <ref> to <sci> using SWarp. Results written to <dest_dir>."""

    ref_name = os.path.basename(ref).replace('.fits', '')
    sci_name = os.path.basename(sci).replace('.fits', '')
    outname = os.path.join(dest_dir, f"{ref_name}_aligned_to_{sci_name}.fits")

    # Run SWarp align
    status = run_swarp_align(ref, sci, source_dir, dest_dir, outname)
    if status != 0:
        logger.error(f"Error occurred in SWarp while aligning reference image to {sci}.")
        return status

    return outname


def run_swarp_align(ref, sci, source_dir, dest_dir, outname, binary=None, dbg=False):
    """Run SWarp (align) (using either the binary specified by [binary] or by
    looking for 'swarp' in the PATH) on the passed <ref> and <sci> images with the results
    and any temporary files created in <dest_dir>. <source_dir> is the path
    to the required config files."""

    status = setup_swarp_dir(source_dir, dest_dir)
    if status != 0:
        return status

    binary = binary or find_binary("swarp")
    if binary is None:
        logger.error("Could not locate 'swarp' executable in PATH")
        return -42

    swarp_config_file = default_swarp_config_files()[0]

    if not os.path.exists(ref):
        logger.error(f"{ref} not found.")
        return -4
    elif not os.path.exists(sci):
        logger.error(f"{sci} not found.")
        return -5

    options = determine_swarp_align_options(ref, sci, dest_dir, outname)

    ref_head = make_ref_head(ref, sci, dest_dir, outname)

    #assemble command line
    cmdline = "%s -c %s %s %s" % (binary, swarp_config_file, ref, options )
    cmdline = cmdline.rstrip()

    #run swarp
    if dbg is True:
        retcode_or_cmdline = cmdline
    else:
        # This executes the command to the terminal
        logger.debug("cmdline=%s" % cmdline)
        args = cmdline.split()
        retcode_or_cmdline = call(args, cwd=dest_dir)

    return retcode_or_cmdline

@timeit
def run_scamp(source_dir, dest_dir, fits_catalog_path, refcatalog='GAIA-DR2.cat', binary=None, dbg=False, distort_degrees=None):
    """Run SCAMP (using either the binary specified by [binary] or by
    looking for 'scamp' in the PATH) on the passed <fits_catalog_path> with the
    results and any temporary files created in <dest_dir>. <source_dir> is the
    path to the required config files."""

    status = setup_scamp_dir(source_dir, dest_dir)
    if status != 0:
        return status

    binary = binary or find_binary("scamp")
    if binary is None:
        logger.error("Could not locate 'scamp' executable in PATH")
        return -42

    scamp_config_file = default_scamp_config_files()[0]
    options = determine_scamp_options(fits_catalog_path, external_cat_name=refcatalog, distort_degrees=distort_degrees)

    # SCAMP writes the output header file to the path that the FITS file is in,
    # not to the directory SCAMP is being run from...
    # If the fits_catalog has a path component, we symlink it to the directory.
    fits_catalog = os.path.basename(fits_catalog_path)
    if fits_catalog != fits_catalog_path:
        fits_catalog = os.path.join(dest_dir, fits_catalog)
        # If the file exists and is a link (or a broken link), then remove it
        if os.path.lexists(fits_catalog):
            if os.path.islink(fits_catalog):
                os.unlink(fits_catalog)
                os.symlink(fits_catalog_path, fits_catalog)
    cmdline = "%s %s -c %s %s" % ( binary, fits_catalog, scamp_config_file, options )
    cmdline = cmdline.rstrip()

    if dbg is True:
        retcode_or_cmdline = cmdline
    else:
        logger.debug("cmdline=%s" % cmdline)
        args = cmdline.split()
        try:
            # Open /dev/null for writing to lose the SCAMP output into
            DEVNULL = open(os.devnull, 'w')
            retcode_or_cmdline = call(args, cwd=dest_dir, stdout=DEVNULL, stderr=DEVNULL, timeout=300)
            DEVNULL.close()
        except TimeoutExpired:
            logger.warning(f'SCAMP timeout reached for {fits_catalog}')
            retcode_or_cmdline = -2

    return retcode_or_cmdline


@timeit
def run_mtdlink(source_dir, dest_dir, fits_file_list, num_fits_files, param_file, pa_rate_dict, catfile_type, binary=None, catalog_type='ASCII', dbg=False):
    """Run MTDLINK (using either the binary specified by [binary] or by
    looking for 'mtdlink' in the PATH) on the passed <fits_files> with the results
    and any temporary files created in <dest_dir>. <source_dir> is the path
    to the required config files."""

    status = setup_mtdlink_dir(source_dir, dest_dir)
    if status != 0:
        return status

    binary = binary or find_binary("mtdlink")
    if binary is None:
        logger.error("Could not locate 'mtdlink' executable in PATH")
        return -42

    mtdlink_config_file = default_mtdlink_config_files()[0]
    options = determine_mtdlink_options(num_fits_files, param_file, pa_rate_dict)

    # MTDLINK wants the input fits files to be in the directory MTDLINK is
    # being run from...
    # If the fits files have a path component, we symlink them to the directory.
    symlink_fits_files = []
    for f in fits_file_list:
        fits_file = os.path.basename(f)
        if fits_file != f:
            fits_file = os.path.join(dest_dir, fits_file)
            if 'BANZAI' not in catfile_type:
                # If the file exists and is a link (or a broken link), then remove it
                if os.path.lexists(fits_file) and os.path.islink(fits_file):
                    os.unlink(fits_file)
                if not os.path.exists(fits_file):
                    # if the file is an e91 and an e11 exists in the working directory, remove the link to the e11 and link the e91
                    if 'e91' in fits_file:
                        if os.path.exists(fits_file.replace('e91.fits', 'e11.fits')):
                            os.unlink(fits_file.replace('e91.fits', 'e11.fits'))
                        os.symlink(f, fits_file)
                    # if the file is an e11 and an e91 doesn't exit in the working directory, create link to the e11
                    elif 'e11' in fits_file and not os.path.exists(fits_file.replace('e11.fits', 'e91.fits')):
                        os.symlink(f, fits_file)
        symlink_fits_files.append(fits_file)

    linked_fits_files = ' '.join(symlink_fits_files)

    # MTDLINK requires an 'MJD' keyword to be in the header.
    # If one doesn't exist, copy 'MJD-OBS' to 'MJD'.
    for f in fits_file_list:
        if os.path.exists(f):
            data, header = fits.getdata(f, header=True)
            if 'MJD' not in header :
                mjd = header['MJD-OBS'] + (0.5*header['exptime']/86400.0)
                header.insert('MJD-OBS', ('MJD', mjd, '[UTC days] Start date/time (Modified Julian Dat'), after=True)
                fits.writeto(f, data, header, overwrite=True, checksum=True)
        else:
            logger.error("Could not find fits file in PATH")
            return -43

    cmdline = "%s %s %s %s %s" % ( 'time', binary, '-verbose', options, linked_fits_files)
    cmdline = cmdline.rstrip()

    if dbg is True:
        retcode_or_cmdline = cmdline
    else:
        logger.debug("cmdline=%s" % cmdline)
        args = cmdline.split()
        # Open mtdlink_output.out for writing the MTDLINK output into
        output_file = open(os.path.join(dest_dir, 'mtdlink_output.out'), 'w')
        retcode_or_cmdline = call(args, cwd=dest_dir, stdout=output_file, stderr=output_file)
        output_file.close()

    return retcode_or_cmdline


def run_findorb(source_dir, dest_dir, obs_file, site_code=500, start_time=datetime.utcnow(), binary=None, dbg=False):
    """Run console version of find_orb in <dest_dir> with input file of MPC1992
    format observations in <obs_file>"""

    status = setup_findorb_dir(source_dir, dest_dir)
    if status != 0:
        return status

    binary = binary or find_binary("fo")
    if binary is None:
        logger.error("Could not locate 'fo' executable in PATH")
        return -42

    setup_findorb_environ_file(source_dir, site_code, start_time)

    # Remove any old version of mpc_fmt.txt
    orbit_file = os.path.join(os.getenv('HOME'), '.find_orb', 'mpc_fmt.txt')
    try:
        os.remove(orbit_file)
    except FileNotFoundError:
        pass

    options = determine_findorb_options(site_code, start_time)
    cmdline = "%s %s %s" % ( binary, obs_file, options)
    cmdline = cmdline.rstrip()
    if dbg:
        print(cmdline)

    if dbg is True:
        retcode_or_cmdline = cmdline
    else:
        logger.debug("cmdline=%s" % cmdline)
        args = cmdline.split()
        retcode_or_cmdline = call(args, cwd=dest_dir)

    return retcode_or_cmdline


#
#
#
#
#


def get_scamp_xml_info(scamp_xml_file):

    # SCAMP VOTable's are malformed and will throw an astropy W42 warning which
    # we don't want. Wrap in context manager to get rid of this
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        try:
            votable = parse(scamp_xml_file)
        except IOError as e:
            logger.error("Unable to open SCAMP VOTable XML file %s (Reason=%s)" % (scamp_xml_file, e))
            return None

    # Extract the Fields and F(ield)Groups tables from the VOTable
    fields_table = votable.get_table_by_id('Fields')
    fgroups_table = votable.get_table_by_id('FGroups')

    reference_catalog = fgroups_table.array['AstRef_Catalog'].data[0]
    # Earlier versions of Astropy (~<3.2.3) have an older VOTable parser which
    # returns `bytes`; later versions return `str`ings
    if type(reference_catalog) == bytes:
        reference_catalog = reference_catalog.decode("utf-8")
    reference_catalog = reference_catalog.replace('-', '')
    if reference_catalog == 'file':
        # SCAMP was fed a reference catalog file, we have more digging to do
        # to get the actual catalog used
        reference_catalog = votable.get_field_by_id_or_name('AstRefCat_Name').value
        if type(reference_catalog) == bytes:
            reference_catalog = reference_catalog.decode("utf-8")
        wcs_refcat_name = reference_catalog
        if '_' in reference_catalog:
            # If it's new format catalog file with position and size, strip
            # these out.
            reference_catalog = reference_catalog.split('_')[0]
        reference_catalog = reference_catalog.replace('.cat', '')
    else:
        wcs_refcat_name = "<Vizier/aserver.cgi?%s@cds>" % reference_catalog.lower()
    wcs_imagecat_name = fields_table.array['Catalog_Name'].data[0]
    if type(wcs_imagecat_name) == bytes:
        wcs_imagecat_name = wcs_imagecat_name.decode("utf-8")
    # Extract AS_Contrast and XY_Contrast as goodness of fit metrics
    as_contrast = fields_table.array['AS_Contrast'].data[0]
    if type(as_contrast) == bytes:
        as_contrast = as_contrast.decode("utf-8")
    xy_contrast = fields_table.array['XY_Contrast'].data[0]
    if type(xy_contrast) == bytes:
        xy_contrast = xy_contrast.decode("utf-8")
    info = { 'num_match'    : fgroups_table.array['AstromNDets_Reference'].data[0],
             'num_refstars' : fields_table.array['NDetect'].data[0],
             'wcs_refcat'   : wcs_refcat_name,
             'wcs_cattype'  : "%s@CDS" % reference_catalog.upper(),
             'wcs_imagecat' : wcs_imagecat_name,
             'pixel_scale'  : fields_table.array['Pixel_Scale'].data[0].mean(),
             'as_contrast'  : as_contrast,
             'xy_contrast'  : xy_contrast,
           }

    return info


def updateFITSWCS(fits_file, scamp_file, scamp_xml_file, fits_file_output):
    """Update the WCS information in a fits file with a bad WCS solution
    using the SCAMP generated FITS-like .head ascii file.
    <fits_file> should the processed CCD image to update, <scamp_file> is
    the SCAMP-produced .head file, <scamp_xml_file> is the SCAMP-produced
    XML output file and <fits_file_output> is the new output FITS file.
    A return status and the updated header are returned; in the event of a
    problem, the status will be -ve and the header will be None"""

    try:
        hdulist = fits.open(fits_file)
        header = hdulist[0].header
        data = hdulist[0].data
    except IOError as e:
        logger.error("Unable to open FITS image %s (Reason=%s)" % (fits_file, e))
        return -1, None

    scamp_info = get_scamp_xml_info(scamp_xml_file)
    if scamp_info is None:
        return -2, None

    try:
        scamp_head_fh = open(scamp_file, 'r')
    except IOError as e:
        logger.error("Unable to open SCAMP header file %s (Reason=%s)" % (scamp_file, e))
        return -3, None

    # Check goodness of fit
    good_fit = True
    if scamp_info['xy_contrast'] < 1.4 or scamp_info['num_match'] < 4:
#    if scamp_info['xy_contrast'] < 0.95 or scamp_info['num_match'] < 4: # More lax constraint for efXX data
        # Bad fit
        logger.warning(f"Bad fit for {os.path.basename(fits_file)} detected. Nmatch={scamp_info['num_match']} XY_contrast={scamp_info['xy_contrast']} AS_contrast={scamp_info['as_contrast']}")
        good_fit = False

    pv_terms = []
    # Read in SCAMP .head file
    for line in scamp_head_fh:
        if 'HISTORY' in line:
            # XXX This should really be a regexp...
            wcssolvr = str(line[34:39]+'-'+line[48:54])
            wcssolvr = wcssolvr.rstrip()
        if 'CTYPE1' in line:
            ctype1 = line[9:31].strip().replace("'", "")
        if 'CTYPE2' in line:
            ctype2 = line[9:31].strip().replace("'", "")
        if 'CUNIT1' in line:
            # Trim spaces, remove single quotes
            cunit1 = line[9:31].strip().replace("'", "")
        if 'CUNIT2' in line:
            cunit2 = line[9:31].strip().replace("'", "")
        if 'CRVAL1' in line:
            crval1 = float(line[9:31])
        if 'CRVAL2' in line:
            crval2 = float(line[9:31])
        if 'CRPIX1' in line:
            crpix1 = float(line[9:31])
        if 'CRPIX2' in line:
            crpix2 = float(line[9:31])
        if 'CD1_1' in line:
            cd1_1 = float(line[9:31])
        if 'CD1_2' in line:
            cd1_2 = float(line[9:31])
        if 'CD2_1' in line:
            cd2_1 = float(line[9:31])
        if 'CD2_2' in line:
            cd2_2 = float(line[9:31])
        if 'ASTIRMS1' in line:
            astirms1 = round(float(line[9:31]), 7)
        if 'ASTIRMS2' in line:
            astirms2 = round(float(line[9:31]), 7)
        if 'ASTRRMS1' in line:
            astrrms1 = round(float(line[9:31])*3600.0, 5)
        if 'ASTRRMS2' in line:
            astrrms2 = round(float(line[9:31])*3600.0, 5)
        if 'PV1_' in line or 'PV2_' in line:
            keyword = line[0:8].rstrip()
            value = float(line[9:31])
            pv_terms.append((keyword, value))
    scamp_head_fh.close()

    # If there are PV terms, check that the CTYPEi is correct
    if len(pv_terms) > 0:
        if 'TAN' in ctype1:
            logger.warning(f"Correcting RA---TAN to RA---TPV in {fits_file}")
            ctype1 = ctype1.replace('TAN', 'TPV')
        if 'TAN' in ctype2:
            logger.warning(f"Correcting DEC--TAN to DEC--TPV in {fits_file}")
            ctype2 = ctype2.replace('TAN', 'TPV')
    # update from scamp xml VOTable
    wcsrfcat = scamp_info['wcs_refcat']
    wcsimcat = scamp_info['wcs_imagecat']
    wcsnref = scamp_info['num_refstars']
    wcsmatch = scamp_info['num_match']
    wccattyp = scamp_info['wcs_cattype']
    secpix = round(scamp_info['pixel_scale'], 6)

    # header keywords we have
    file_bits = fits_file_output.split(os.extsep)
    new_red_level = 91
    if len(file_bits) == 2:
        filename_noext = file_bits[0]
        new_red_level = int(filename_noext[-2:])
    # Swope files don't have a RLEVEL header so assume one corresponding to the proc level
    if new_red_level != header.get('rlevel', 71):
        print(f"Updating header RLEVEL to: {new_red_level}")
        header['RLEVEL'] = new_red_level
    header['PCRECIPE'] = 'BANZAI'
    header['PPRECIPE'] = 'NEOEXCHANGE'
    # WCS headers
    if good_fit:
        header['WCSDELRA'] = ((header['CRVAL1'] - crval1)*3600.0, '[arcsec] Shift of fitted WCS w.r.t. nominal')
        header['WCSDELDE'] = ((header['CRVAL2'] - crval2)*3600.0, '[arcsec] Shift of fitted WCS w.r.t. nominal')
        header['CTYPE1'] = ctype1
        header['CTYPE2'] = ctype2
        header['CRVAL1'] = crval1
        header['CRVAL2'] = crval2
        header['CRPIX1'] = crpix1
        header['CRPIX2'] = crpix2
        header['CD1_1'] = cd1_1
        header['CD1_2'] = cd1_2
        header['CD2_1'] = cd2_1
        header['CD2_2'] = cd2_2
        header['SECPIX'] = (secpix, '[arcsec/pixel] Fitted pixel scale on sky')
    else:
        astrrms1 = -99.0
        astrrms2 = -99.0
    header['WCSSOLVR'] = (wcssolvr, 'WCS solver')
    # This can be quite long and the comment might not fit. Truncate at max possible length
    existing_length = 11 + len(wcsrfcat) + 4 # 8 (keyword) + "= '" + catname length + "' / '"
    comment_length = max(80-existing_length, 0)
    header['WCSRFCAT'] = (wcsrfcat, 'Fname of astrometric catalog'[0:comment_length])
    # This can be quite long and the comment might not fit. Truncate at max possible length
    existing_length = 11 + len(wcsimcat) + 4 # 8 (keyword) + "= '" + catname length + "' / '"
    comment_length = max(80-existing_length, 0)
    header['WCSIMCAT'] = (wcsimcat, 'Fname of detection catalog'[0:comment_length])
    header['WCSNREF']  = (wcsnref, 'Stars in image available to define WCS')
    header['WCSMATCH'] = (wcsmatch, 'Stars in image matched against ref catalog')
    header['WCCATTYP'] = (wccattyp, 'Reference catalog used')
    header['WCSRDRES'] = (str(str(astrrms1)+'/'+str(astrrms2)), '[arcsec] WCS fitting residuals (x/y)')
    if good_fit:
        header['WCSERR'] = 0
        status = 0
    else:
        header['WCSERR'] = 5
        status = -5

    # header keywords we (probably) don't have. Insert after CTYPE2
    if header.get('CUNIT1', None) is None:
        header.insert('CTYPE2', ('CUNIT1', cunit1, 'Unit of 1st axis'), after=True)
    if header.get('CUNIT2', None) is None:
        header.insert('CUNIT1', ('CUNIT2', cunit2, 'Unit of 2nd axis'), after=True)

    # Add distortion keywords if present
    if good_fit:
        prior_keyword = 'CD2_2'
        for keyword, value in pv_terms:
            header.insert(prior_keyword, (keyword, value, 'TPV distortion coefficient'), after=True)
            prior_keyword = keyword

    hdu = fits.PrimaryHDU(data, header)
    hdu._bscale = 1.0
    hdu._bzero = 0.0
    hdu.header.remove("BSCALE", ignore_missing=True)
    hdu.header.insert("NAXIS2", ("BSCALE", 1.0), after=True)
    hdu.header.remove("BZERO", ignore_missing=True)
    hdu.header.insert("BSCALE", ("BZERO", 0.0), after=True)
    new_hdulist = fits.HDUList([hdu,])

    for index, hdu in enumerate(hdulist[1:]):
        logger.info(f"{index} {hdu.name}X {hdu._summary()}")
        if hdu.name != 'SCI':
            if hasattr(hdu, 'compressed_data'):
                new_hdu = fits.ImageHDU(data=hdu.data, header=hdu.header, name=hdu.name)
            else:
                new_hdu = hdu
            new_hdulist.append(new_hdu)

    # Need to force the CHECKSUM to be recomputed. Trap for young players..
    new_hdulist.writeto(fits_file_output, overwrite=True, checksum=True)

    hdulist.close()
    new_hdulist.close()

    return status, header


def updateFITScalib(header, fits_file, catalog_type='BANZAI'):
    """Updates or adds the zeropoint and photometric calibration keywords in <fits_file>
    """
    status = 0

    keywords = OrderedDict([
                    ('zeropoint'     , 'Instrumental zeropoint [mag]'),
                    ('zeropoint_err' , 'Error on Instrumental zeropoint [mag]'),
                    ('zeropoint_src' , 'Source of Instrumental zeropoint'),
                    ('color_used'    , 'Color used for calibration'),
                    ('color'         , 'Color coefficient [mag]'),
                    ('color_err'     , 'Error on color coefficient [mag]'),
                    ('photometric_catalog', 'Photometric catalog used')
                 ])
    header_items = {}
    if catalog_type == 'BANZAI':
        hdr_mapping, tbl_mapping = banzai_catalog_mapping()
    elif catalog_type == 'BANZAI_LDAC':
        hdr_mapping, tbl_mapping = banzai_ldac_catalog_mapping()
    else:
        logger.error(f"Unsupported catalog mapping: {catalog_type}")
        return -2, None

    try:
        hdulist = fits.open(fits_file)
    except IOError as e:
        logger.error(f"Unable to open FITS image {fits_file} (Reason={e})")
        return -1, None

    if catalog_type == 'BANZAI':
        fits_header = hdulist[0].header
    else:
        header_array = hdulist[1].data[0][0]
        fits_header = fits_ldac_to_header(header_array)

    # Find place to start inserting
    if "PNTOFST" in fits_header:
        prior_keyword = "PNTOFST"
    elif "L1ELLIPA" in fits_header:
        prior_keyword = "L1ELLIPA"
    else:
        prior_keyword = None
    #print(f"Initial prior_keyword= {prior_keyword}")
    for key, comment in keywords.items():
        new_val = header.get(key, None)
        if new_val:
            fits_keyword = hdr_mapping.get(key, '')
            fits_keyword = fits_keyword.replace('<', '').replace('>', '')
            if fits_keyword != '':
                #print(fits_keyword, new_val, comment, prior_keyword)
                fits_header.set(fits_keyword, new_val, comment, after=prior_keyword)
                prior_keyword = fits_keyword
            else:
                logger.warning(f"FITS Keyword not found for {key}")

    if catalog_type == 'BANZAI_LDAC':
        # Construct new BinTable from lengthened header

        newhdr_string = fits_header.tostring(endcard=False)
        hdr_col = fits.Column(name='Field Header Card', format=f'{len(newhdr_string)}A',
                          array=[newhdr_string])
        hdrhdu = fits.BinTableHDU.from_columns(fits.ColDefs([hdr_col]))
        hdrhdu.header['EXTNAME'] = 'LDAC_IMHEAD'
        dim2 = int(len(newhdr_string) / 80)
        hdrhdu.header['TDIM1'] = (f'(80, {dim2})')
        hdulist[1] = hdrhdu

    fits_file_output = fits_file
    hdulist.writeto(fits_file_output, overwrite=True, checksum=True)

    return status, fits_header

def read_mtds_file(mtdsfile, dbg=False):
    """Read a detections file produced by mtdlink and return a dictionary of the
    version number, number of frames, number of detections and a list of
    detections (as #frames x 20 column numpy arrays)"""

    try:
        mtds_fh = open(mtdsfile, 'r')
    except IOError:
        return {}

    # Read header
    version = mtds_fh.readline().rstrip()
    frames_string = mtds_fh.readline()
    num_frames = frames_string.split('/')[0]
    num_frames = int(num_frames.rstrip())

    frame = 0
    frames = []
    while frame < num_frames:
        frame_string = mtds_fh.readline()
        if dbg:
            print(frame, frame_string)
        frame_chunks = frame_string.split(' ')
        frame_filename = frame_chunks[0]
        frame_jd = float(frame_chunks[1])

        # basic check that the JD is within the expected range
        # values are 2014-01-01 to 2036-12-31 converted to Julian Dates
        if frame_jd < 2456658.5 or frame_jd > 2465058.5:
            logger.warning("Frame %s has suspicious JD value %f outside expected range" % (frame_filename, frame_jd))
        frames.append((frame_filename, frame_jd))
        frame += 1

    # Suck in rows and columns of detections into a numpy array. The shape should
    # (# detections x # frames, 20). We can divide the number of rows by the
    # number of frames and that will give us the number of detections.
    # If we then vertically split the array on the number of detections, we
    # will get # detection sub arrays of # frames x 20 columns which we can
    # pickle/store later

    dtypes = detections_array_dtypes()

    with warnings.catch_warnings():
        warnings.simplefilter('error', UserWarning)
        try:
            dets_array = loadtxt(mtds_fh, dtype=dtypes)
        except Exception as e:
            logger.warning("Didn't find any detections in file %s (Reason %s)" % (mtdsfile, e))
            dets_array = empty( shape=(0, 0))

    # Check for correct number of entries
    if dbg:
        print(dets_array.shape)
    num_detections = dets_array.shape[0] / num_frames
    if num_detections == 0:
        logger.warning("Found 0 detection entries")
        num_detections = 0
        detections = []
    elif dets_array.shape[0] / float(num_frames) != num_detections:
        logger.error("Incorrect number of detection entries (Expected %d, got %d)" % (num_frames*num_detections, dets_array.shape[0]))
        num_detections = 0
        detections = []
    if num_detections:
        detections = split(dets_array, num_detections)
    mtds_fh.close()

    # Assemble dictionary'o'stuff...
    dets = { 'version' : version,
             'num_frames' : num_frames,
             'frames' : frames,
             'num_detections' : num_detections,
             'detections' : detections
           }

    return dets


def unpack_tarball(tar_path, unpack_dir):
    """unpacks tarballs and puts files in appropriately named directory with appropriate permissions"""
    unpack_archive(tar_path, extract_dir=unpack_dir, format="gztar")

    os.chmod(unpack_dir, 0o775)
    files = glob(unpack_dir+'/*')

    for file in files:
        os.chmod(file, 0o664)

    return files


def run_damit_periodscan(lcs_input_filename, psinput_filename, psoutput_filename, binary=None, dbg=False):
    """ Run DAMIT code to calculate periodogram based on lc .
        See https://astro.troja.mff.cuni.cz/projects/damit/
    """
    binary = binary or find_binary("period_scan")
    if binary is None:
        logger.error("Could not locate 'period_scan' executable in PATH")
        return -42
    dest_dir = os.path.dirname(psoutput_filename)
    cmdline = f"{binary} -v {psinput_filename} {psoutput_filename}"
    catline = f"cat {lcs_input_filename}"
    cmdline = cmdline.rstrip()
    catline = catline.rstrip()
    if dbg:
        print(cmdline)

    if dbg is True:
        retcode_or_cmdline = cmdline
    else:
        logger.debug(f"cmdline={catline} | {cmdline}")
        cmd_args = cmdline.split()
        cat_args = catline.split()
        cat_call = Popen(cat_args, cwd=dest_dir, stdout=PIPE)
        cmd_call = Popen(cmd_args, cwd=dest_dir, stdin=cat_call.stdout, stdout=PIPE)
        retcode_or_cmdline = cmd_call.communicate()

    return retcode_or_cmdline


def run_damit(call_name, cat_input_filename, primary_call, write_out=False, binary=None, dbg=False):
    """ Run DAMIT code to calculate LC and shape models.
        See https://astro.troja.mff.cuni.cz/projects/damit/
    """
    binary = binary or find_binary(call_name)
    if binary is None:
        logger.error(f"Could not locate {call_name} executable in PATH")
        return -42
    dest_dir = os.path.dirname(cat_input_filename)
    cmdline = f"{binary} {primary_call}"
    catline = f"cat {cat_input_filename}"
    cmdline = cmdline.rstrip()
    catline = catline.rstrip()
    if dbg:
        print(cmdline)

    if dbg is True:
        retcode_or_cmdline = cmdline
    else:
        logger.debug(f"cmdline={catline} | {cmdline}")
        cmd_args = cmdline.split()
        cat_args = catline.split()
        cat_call = Popen(cat_args, cwd=dest_dir, stdout=PIPE)
        if write_out:

            cmd_call = Popen(cmd_args, cwd=dest_dir, stdin=cat_call.stdout, stdout=write_out)
        else:
            cmd_call = Popen(cmd_args, cwd=dest_dir, stdin=cat_call.stdout, stdout=PIPE)
        retcode_or_cmdline = cmd_call.communicate()

    return retcode_or_cmdline

def run_astcrop(filename, dest_dir, xmin, xmax, ymin, ymax, binary='astcrop', dbg=False):
    '''
    Crops the passed <filename> using astcrop to xmin:xmax,ymin:ymax pixel extent,
    writing output to <dest_dir>
    '''
    if filename is None:
        return None, -2
    if os.path.exists(filename) is False:
        return None, -1

    binary = binary or find_binary(binary)
    if binary is None:
        logger.error(f"Could not locate {binary} executable in PATH")
        return None, -42

#for hdu in $(astfits /apophis/cora/didymos_data/outputs_segstack7/20230223/elp1m006-fa07-20230223-0160-e92-combine-superstack-chisel.fits --listimagehdus); do
#  astcrop --mode=img  --section=1:1991,1:511 $filename --hdu=$hdu --append --output=$cropped_filename --metaname=$hdu;  done

    cropped_filename, options = determine_astcrop_options(filename, dest_dir, xmin, xmax, ymin, ymax)
    if os.path.exists(cropped_filename):
        return cropped_filename, 1

    with fits.open(filename) as hdulist:
        hdu_names = [hdu.name for hdu in hdulist]

    for hdu in hdu_names:
        cmdline = f"{binary} "
        if hdu == '':
            cmdline += options.replace('--hdu=<hdu>', '').replace('--metaname=<hdu>', '')
        else:
            cmdline += options.replace('<hdu>', hdu)
        cmdline = cmdline.rstrip()
        if dbg:
            print(cmdline)

        if dbg is True:
            retcode_or_cmdline = cmdline
        else:
            logger.debug(f"cmdline={cmdline}")
            cmd_args = cmdline.split()
            cmd_call = Popen(cmd_args, cwd=dest_dir, stdout=PIPE)
            (out, errors) = cmd_call.communicate()
            retcode_or_cmdline = cmd_call.returncode

    return cropped_filename, retcode_or_cmdline

def run_astwarp(filename, dest_dir, center_RA, center_DEC, width = 1991.0, height = 511.0, binary='astwarp', dbg=False):
    '''
    Runs astwarp on <filename> to crop to <center_RA>,<center_DEC> with 
    [width]x[height] writing output to <dest_dir>
    '''
    if filename is None:
        return None, -2
    if os.path.exists(filename) is False:
        return None, -1
    with fits.open(filename) as hdulist:
        header = hdulist['NOISECHISEL-CONFIG'].header
        input_1 = header['INPUT_1']
        input_2 = header['INPUT_2']
    input_filename = os.path.join(input_1, input_2)
    header, dummy_table, cattype = open_fits_catalog(input_filename, header_only=True)
    wcs_err = header['WCSERR']
    if wcs_err != 0:
        return None, -5
    binary = binary or find_binary(binary)
    if binary is None:
        logger.error(f"Could not locate {binary} executable in PATH")
        return None, -42
    cmdline = f"{binary} "

    wcs = WCS(header)
    #print(header['NAXIS1'], header['NAXIS2'])
    x, y = wcs.world_to_pixel_values(center_RA, center_DEC)
    rot_angle = get_rot(wcs)
    #print(f"{os.path.basename(input_filename)}: {x:.3f} {y:.3f} PA= {rot_angle:+.2f}")
    # Offset by 30% of width to put comet/Didymos at left 20% of crop
    shift = -0.3
    if rot_angle > 0:
        shift = 0.3
    new_center_RA, new_center_DEC = wcs.pixel_to_world_values(x+(shift*width), y)
    #print(f"{center_RA}->{new_center_RA}, {center_DEC}->{new_center_DEC} {shift} {x+(shift*width)}, {y}")
    x_max = header['NAXIS1']
    y_max = header['NAXIS2']
    if x<0 or x>x_max or y<0 or y>y_max:
        return None, -3
    if width>x_max or height>y_max:
        return None, -4
    cropped_filename, options = determine_astwarp_options(filename, dest_dir, new_center_RA, new_center_DEC, width, height)
    if os.path.exists(cropped_filename):
        return cropped_filename, 1
    cmdline += options
    cmdline = cmdline.rstrip()
    if dbg:
        print(cmdline)

    if dbg is True:
        retcode_or_cmdline = cmdline
    else:
        logger.debug(f"cmdline={cmdline}")
        cmd_args = cmdline.split()
        cmd_call = Popen(cmd_args, cwd=dest_dir, stdout=PIPE)
        (out, errors) = cmd_call.communicate()
        retcode_or_cmdline = cmd_call.returncode

    return cropped_filename, retcode_or_cmdline

def run_astarithmetic(input_filenames, dest_dir, hdu = 'ALIGNED', binary='astarithmetic', dbg=False):
    '''
    Runs astarithmetic on list of <filenames> to mean combine creating a
    stack writing output to <dest_dir>
    '''
    filenames=[]
    for filename in input_filenames:
        if filename is not None:
            filenames.append(filename)
    if len(filenames)==0:
        return None, -6
    #print(filenames)
    for filename in filenames:
        if os.path.exists(filename) is False:
            return None, -1
    binary = binary or find_binary(binary)
    if binary is None:
        logger.error(f"Could not locate {binary} executable in PATH")
        return None, -42
    cmdline = f"{binary} "
    combined_filename, options = determine_astarithmetic_options(filenames, dest_dir, hdu)
    if os.path.exists(combined_filename):
        return combined_filename, 1
    cmdline += options
    cmdline = cmdline.rstrip()
    if dbg:
        print(cmdline)

    if dbg is True:
        retcode_or_cmdline = cmdline
    else:
        logger.debug(f"cmdline={cmdline}")
        cmd_args = cmdline.split()
        cmd_call = Popen(cmd_args, cwd=dest_dir, stdout=PIPE)
        (out, errors) = cmd_call.communicate()
        retcode_or_cmdline = cmd_call.returncode

    return combined_filename, retcode_or_cmdline

def run_didymos_astarithmetic(filename, dest_dir, didymos_id, binary='astarithmetic', dbg=False):
    '''
    Runs astarithmetic on <filename> to extract didymos_detection writing
    output to <dest_dir>
    '''
    if filename is None:
        return None, -2
    if os.path.exists(filename) is False:
        return None, -1
    binary = binary or find_binary(binary)
    if binary is None:
        logger.error(f"Could not locate {binary} executable in PATH")
        return None, -42
    cmdline = f"{binary} "
    extracted_filename, options = determine_didymos_extraction_options(filename, dest_dir, didymos_id)
    if os.path.exists(extracted_filename):
        return extracted_filename, 1
    cmdline += options
    cmdline = cmdline.rstrip()
    if dbg:
        print(cmdline)

    if dbg is True:
        retcode_or_cmdline = cmdline
    else:
        logger.debug(f"cmdline={cmdline}")
        cmd_args = cmdline.split()
        cmd_call = Popen(cmd_args, cwd=dest_dir, stdout=PIPE)
        (out, errors) = cmd_call.communicate()
        retcode_or_cmdline = cmd_call.returncode

    return extracted_filename, retcode_or_cmdline

def run_didymos_bordergen(filename, dest_dir, didymos_id, binary='astarithmetic', all_borders=False, dbg=False):
    '''
    Runs astarithmetic on <filename> to extract the detection border around
    Didymos only ([all_borders]=False) or all detections ([all_borders=True)
    converting it to JPG and writing this output to <dest_dir>
    '''
    if filename is None:
        return None, -2
    if os.path.exists(filename) is False:
        return None, -1
    binary = binary or find_binary(binary)
    if binary is None:
        logger.error(f"Could not locate {binary} executable in PATH")
        return None, -42
    cmdline = f"{binary} "
    fits_image_filename, options = determine_didymos_border_options(filename, dest_dir, didymos_id, all_borders)
    if os.path.exists(fits_image_filename) is False:
        cmdline += options
        cmdline = cmdline.rstrip()
        if dbg:
            print(cmdline)

        if dbg is True:
            retcode_or_cmdline = cmdline
        else:
            logger.debug(f"cmdline={cmdline}")
            cmd_args = cmdline.split()
            cmd_call = Popen(cmd_args, cwd=dest_dir, stdout=PIPE)
            (out, errors) = cmd_call.communicate()
            retcode_or_cmdline = cmd_call.returncode

    # Convert FITS to JPG
    image_filename, retcode_or_cmdline = run_astconvertt(fits_image_filename, dest_dir, out_type='jpg', hdu=1, stack=False, dbg=dbg)

    return image_filename, retcode_or_cmdline

def run_astnoisechisel(filename, dest_dir, hdu = 0, binary='astnoisechisel', bkgd_only=False, dbg=False):
    '''
    Runs astnoisechisel on <filename> to produce a binary detection map
    writing output to <dest_dir>
    '''
    if filename is None:
        return None, -2
    if os.path.exists(filename) is False:
        return None, -1
    binary = binary or find_binary(binary)
    if binary is None:
        logger.error(f"Could not locate {binary} executable in PATH")
        return None, -42
    cmdline = f"{binary} "
    chiseled_filename, options = determine_astnoisechisel_options(filename, dest_dir, hdu, bkgd_only)
    if os.path.exists(chiseled_filename):
        return chiseled_filename, 1
    cmdline += options
    cmdline = cmdline.rstrip()
    if dbg:
        print(cmdline)

    if dbg is True:
        retcode_or_cmdline = cmdline
    else:
        logger.debug(f"cmdline={cmdline}")
        cmd_args = cmdline.split()
        cmd_call = Popen(cmd_args, cwd=dest_dir, stdout=PIPE)
        (out, errors) = cmd_call.communicate()
        retcode_or_cmdline = cmd_call.returncode

    return chiseled_filename, retcode_or_cmdline

def run_aststatistics(filename, keyword, hdu='SCI', binary='aststatistics', dbg=False):
    '''
    Runs aststatistics on <filename> to find either the sigma-clipped mean
    or the sigma-clipped standard deviation depending on the provided <keyword>
    '''
    if filename is None:
        return None, -2
    if os.path.exists(filename) is False:
        return None, -1
    binary = binary or find_binary(binary)
    if binary is None:
        logger.error(f"Could not locate {binary} executable in PATH")
        return None, -42
    cmdline = f"{binary} {filename} -h{hdu} --sigclip-{keyword}"
    cmdline = cmdline.rstrip()
    if dbg:
        print(cmdline)

    if dbg is True:
        retcode_or_cmdline = cmdline
        out = None
    else:
        logger.debug(f"cmdline={cmdline}")
        cmd_args = cmdline.split()
        cmd_call = Popen(cmd_args, stdout=PIPE)
        (out, errors) = cmd_call.communicate()
        retcode_or_cmdline = cmd_call.returncode

    return out, retcode_or_cmdline

def run_astconvertt(filename, dest_dir, out_type='pdf', hdu='SCI', mean=0, std=0, stack=True, binary='astconvertt', dbg=False):
    '''
    Runs astconvertt on <filename> to convert .fits file to .<out_type> file writing
    output to <dest_dir>
    '''
    if filename is None:
        return None, -2
    if os.path.exists(filename) is False:
        return None, -1
    binary = binary or find_binary(binary)
    if binary is None:
        logger.error(f"Could not locate {binary} executable in PATH")
        return None, -42
    cmdline = f"{binary} "
    if stack:
        pdf_filename, options = determine_stack_astconvertt_options(filename, dest_dir, mean, std, out_type, hdu)
    else:
        pdf_filename, options = determine_astconvertt_options(filename, dest_dir, out_type, hdu)
    if os.path.exists(pdf_filename):
        return pdf_filename, 1
    cmdline += options
    cmdline = cmdline.rstrip()
    if dbg:
        print(cmdline)

    if dbg is True:
        retcode_or_cmdline = cmdline
    else:
        logger.debug(f"cmdline={cmdline}")
        cmd_args = cmdline.split()
        cmd_call = Popen(cmd_args, cwd=dest_dir, stdout=PIPE)
        (out, errors) = cmd_call.communicate()
        retcode_or_cmdline = cmd_call.returncode

    return pdf_filename, retcode_or_cmdline

def run_astmkcatalog(filename, dest_dir, binary='astmkcatalog', dbg=False):
    '''
    Runs astmkcatalog on <filename> to make a catalog writing output to <dest_dir>
    '''
    if filename is None:
        return None, -2
    if os.path.exists(filename) is False:
        return None, -1
    binary = binary or find_binary(binary)
    if binary is None:
        logger.error(f"Could not locate {binary} executable in PATH")
        return None, -42
    cmdline = f"{binary} "
    catalog_filename, options = determine_astmkcatalog_options(filename, dest_dir)
    if os.path.exists(catalog_filename):
        return catalog_filename, 1
    cmdline += options
    cmdline = cmdline.rstrip()
    if dbg:
        print(cmdline)

    if dbg is True:
        retcode_or_cmdline = cmdline
    else:
        logger.debug(f"cmdline={cmdline}")
        cmd_args = cmdline.split()
        cmd_call = Popen(cmd_args, cwd=dest_dir, stdout=PIPE)
        (out, errors) = cmd_call.communicate()
        retcode_or_cmdline = cmd_call.returncode

    return catalog_filename, retcode_or_cmdline

def run_asttable(filename, dest_dir, binary='asttable', dbg=False):
    '''
    Runs asttable on <filename> to make .txt version of the catalog writing
    output to <dest_dir>
    '''
    if filename is None:
        return None, -2
    if os.path.exists(filename) is False:
        return None, -1
    binary = binary or find_binary(binary)
    if binary is None:
        logger.error(f"Could not locate {binary} executable in PATH")
        return None, -42
    cmdline = f"{binary} "
    table_filename, options = determine_asttable_options(filename, dest_dir)
    if os.path.exists(table_filename):
        return table_filename, 1
    cmdline += options
    cmdline = cmdline.rstrip()
    if dbg:
        print(cmdline)

    if dbg is True:
        retcode_or_cmdline = cmdline
    else:
        logger.debug(f"cmdline={cmdline}")
        cmd_args = cmdline.split()
        cmd_call = Popen(cmd_args, cwd=dest_dir, stdout=PIPE)
        (out, errors) = cmd_call.communicate()
        retcode_or_cmdline = cmd_call.returncode

    return table_filename, retcode_or_cmdline
