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
from math import floor
from datetime import datetime
from subprocess import call
from collections import OrderedDict
import warnings
from shutil import unpack_archive
from glob import glob

from astropy.io import fits
from astropy.io.votable import parse
from numpy import loadtxt, split, empty

from core.models import detections_array_dtypes
from astrometrics.time_subs import timeit
from photometrics.catalog_subs import oracdr_catalog_mapping

logger = logging.getLogger(__name__)


def default_mtdlink_config_files():
    """Return a list of the needed files for MTDLINK. The config file should be in
    element 0"""

    config_files = ['mtdi.lcogt.param']

    return config_files


def default_scamp_config_files():
    """Return a list of the needed files for SCAMP. The config file should be in
    element 0"""

    config_files = ['scamp_neox.cfg']

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
    elif catalog_type == 'CSS:ASCII_HEAD':
        config_files = ['sextractor_CSS_ascii.conf',
                        'sextractor_CSS_ascii.params']
    config_files = config_files + common_config_files
    return config_files


def default_findorb_config_files():
    config_files = ['environ.def', 'ps_1996.dat', 'elp82.dat']
    return config_files


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
            print(line.rstrip(), file=out_fh)

    return


def setup_working_dir(source_dir, dest_dir, config_files):
    """Sets up a temporary working directory for running programs in <dest_dir>.
    The temporary working directory is created if needed and the required config
    files (given in a list in <config_files>) are symlinked from <source_dir> if
    they don't already exist in <dest_dir>"""

    if not os.path.exists(source_dir):
        logger.error("Source path '%s' does not exist" % source_dir)
        return -1

    if not os.path.exists(dest_dir):
        try:
            os.makedirs(dest_dir)
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


def determine_sext_options(fits_file):

    option_mapping = OrderedDict([
                        ('gain'      , '-GAIN'),
                        ('zeropoint' , '-MAG_ZEROPOINT'),
                        ('pixel_scale' , '-PIXEL_SCALE'),
                        ('saturation'  , '-SATUR_LEVEL'),
                     ])

    options = ''
    if not os.path.exists(fits_file):
        logger.error("FITS file %s does not exist" % fits_file)
        return options
    try:
        hdulist = fits.open(fits_file)
    except IOError as e:
        logger.error("Unable to open FITS image %s (Reason=%s)" % (fits_file, e))
        return options

    header = hdulist[0].header
    header_mapping, table_mapping = oracdr_catalog_mapping()

    for option in option_mapping.keys():
        if header.get(header_mapping[option], -99) != -99:
            options += option_mapping[option] + ' ' + str(header.get(header_mapping[option])) + ' '
    options = options.rstrip()
    return options


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


def determine_scamp_options(fits_catalog):

    options = ''

    return options


def determine_findorb_options(site_code):
    """Options for find_orb:
    -z: use config directory for files (in $HOME/.find_orb),
    -q: quiet,
    -C <code>: set MPC site code for ephemeris to <code>,
    -e new.ephem: output ephemeris to new.ephem
    -c combine designations
    """

    options = "-z -c -q -C {} -e new.ephem".format(site_code)

    return options


def add_l1filter(fits_file):
    """Adds a L1FILTER keyword into the <fits_file> with the same value
    as FILTER. If not found, nothing is done."""

    hdulist = fits.open(fits_file, mode='update')
    prihdr = hdulist[0].header
    filter_val = prihdr.get('FILTER', None)
    if filter_val:
        prihdr['L1FILTER'] = (filter_val, 'Copy of FILTER for SCAMP')
    hdulist.close()

    return


@timeit
def run_sextractor(source_dir, dest_dir, fits_file, binary=None, catalog_type='ASCII', dbg=False, aperture=None):
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

    # If we are making FITS_LDAC catalogs for SCAMP, we need to create a new
    # header keyword of L1FILTER and set the value to FILTER. This prevents
    # SCAMP false matching on the first FITS keyword starting with FILTER
    if catalog_type == 'FITS_LDAC':
        root_fits_file = fits_file
        if '[SCI]' in fits_file:
            # Banzai format, strip off extension
            root_fits_file = fits_file.replace('[SCI]', '')
        add_l1filter(root_fits_file)

    sextractor_config_file = default_sextractor_config_files(catalog_type)[0]
    if '[SCI]' in fits_file:
        options = determine_sext_options(root_fits_file)
    else:
        options = determine_sext_options(fits_file)
    if aperture is not None:
        options += " -PHOT_APERTURES {:.2f}".format(aperture)
    cmdline = "%s %s -c %s %s" % ( binary, fits_file, sextractor_config_file, options )
    cmdline = cmdline.rstrip()

    if dbg is True:
        retcode_or_cmdline = cmdline
    else:
        logger.debug("cmdline=%s" % cmdline)
        args = cmdline.split()
        retcode_or_cmdline = call(args, cwd=dest_dir)

    return retcode_or_cmdline


@timeit
def run_scamp(source_dir, dest_dir, fits_catalog_path, binary=None, dbg=False):
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
    options = determine_scamp_options(fits_catalog_path)

    # SCAMP writes the output header file to the path that the FITS file is in,
    # not to the directory SCAMP is being run from...
    # If the fits_catalog has a path component, we symlink it to the directory.
    fits_catalog = os.path.basename(fits_catalog_path)
    if fits_catalog != fits_catalog_path:
        fits_catalog = os.path.join(dest_dir, fits_catalog)
        # If the file exists and is a link (or a broken link), then remove it
        if os.path.lexists(fits_catalog) and os.path.islink(fits_catalog):
            os.unlink(fits_catalog)
        os.symlink(fits_catalog_path, fits_catalog)
    cmdline = "%s %s -c %s %s" % ( binary, fits_catalog, scamp_config_file, options)
    cmdline = cmdline.rstrip()

    if dbg is True:
        retcode_or_cmdline = cmdline
    else:
        logger.debug("cmdline=%s" % cmdline)
        args = cmdline.split()
        # Open /dev/null for writing to lose the SCAMP output into
        DEVNULL = open(os.devnull, 'w')
        retcode_or_cmdline = call(args, cwd=dest_dir, stdout=DEVNULL, stderr=DEVNULL)
        DEVNULL.close()

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

    options = determine_findorb_options(site_code)
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
    reference_catalog = reference_catalog.decode("utf-8")
    reference_catalog = reference_catalog.replace('-', '')
    info = { 'num_match'    : fgroups_table.array['AstromNDets_Internal_HighSN'].data[0],
             'num_refstars' : fields_table.array['NDetect'].data[0],
             'wcs_refcat'   : "<Vizier/aserver.cgi?%s@cds>" % reference_catalog.lower(),
             'wcs_cattype'  : "%s@CDS" % reference_catalog.upper(),
             'wcs_imagecat' : fields_table.array['Catalog_Name'].data[0].decode("utf-8"),
             'pixel_scale'  : fields_table.array['Pixel_Scale'].data[0].mean()
           }

    return info


def updateFITSWCS(fits_file, scamp_file, scamp_xml_file, fits_file_output):
    """Update the WCS information in a fits file with a bad WCS solution
    using the SCAMP generated FITS-like .head ascii file.
    <fits_file> should the processed CCD image to update, <scamp_file> is
    the SCAMP-produced .head file, <scamp_xml_file> is the SCAMP-produced
    XML output file and <fits_file_output> is the new output FITS file."""

    try:
        data, header = fits.getdata(fits_file, header=True)
    except IOError as e:
        logger.error("Unable to open FITS image %s (Reason=%s)" % (fits_file, e))
        return -1

    scamp_info = get_scamp_xml_info(scamp_xml_file)
    if scamp_info is None:
        return -2

    try:
        scamp_head_fh = open(scamp_file, 'r')
    except IOError as e:
        logger.error("Unable to open SCAMP header file %s (Reason=%s)" % (scamp_file, e))
        return -3

    # Read in SCAMP .head file
    for line in scamp_head_fh:
        if 'HISTORY' in line:
            wcssolvr = str(line[34:39]+'-'+line[48:53])
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
    scamp_head_fh.close()

    # update from scamp xml VOTable
    wcsrfcat = scamp_info['wcs_refcat']
    wcsimcat = scamp_info['wcs_imagecat']
    wcsnref = scamp_info['num_refstars']
    wcsmatch = scamp_info['num_match']
    wccattyp = scamp_info['wcs_cattype']
    secpix = round(scamp_info['pixel_scale'], 6)

    # header keywords we have
    header['WCSDELRA'] = header['CRVAL1'] - crval1
    header['WCSDELDE'] = header['CRVAL2'] - crval2
    header['CRVAL1'] = crval1
    header['CRVAL2'] = crval2
    header['CRPIX1'] = crpix1
    header['CRPIX2'] = crpix2
    header['CD1_1'] = cd1_1
    header['CD1_2'] = cd1_2
    header['CD2_1'] = cd2_1
    header['CD2_2'] = cd2_2
    header['SECPIX'] = (secpix, '[arcsec/pixel] Fitted pixel scale on sky')
    header['WCSSOLVR'] = wcssolvr
    header['WCSRFCAT'] = wcsrfcat
    header['WCSIMCAT'] = wcsimcat
    header['WCSNREF'] = wcsnref
    header['WCSMATCH'] = wcsmatch
    header['WCCATTYP'] = wccattyp
    header['WCSRDRES'] = str(str(astrrms1)+'/'+str(astrrms2))
    header['WCSERR'] = 0

    # header keywords we (probably) don't have. Insert after CTYPE2
    if header.get('CUNIT1', None) is None:
        header.insert('CTYPE2', ('CUNIT1', cunit1, 'Unit of 1st axis'), after=True)
    if header.get('CUNIT2', None) is None:
        header.insert('CUNIT1', ('CUNIT2', cunit2, 'Unit of 2nd axis'), after=True)

    # Need to force the CHECKSUM to be recomputed. Trap for young players..
    fits.writeto(fits_file_output, data, header, overwrite=True, checksum=True)

    return 0


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
