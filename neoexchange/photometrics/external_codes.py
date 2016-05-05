'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2016-2016 LCOGT

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''

import logging
import os
from math import floor
from subprocess import call
from collections import OrderedDict
import warnings

from astropy.io import fits
from astropy.io.votable import parse

from astrometrics.time_subs import timeit
from photometrics.catalog_subs import oracdr_catalog_mapping

logger = logging.getLogger(__name__)

def default_mtdlink_config_files():
    '''Return a list of the needed files for MTDLINK. The config file should be in
    element 0'''

    config_files = ['mtdi.lcogt.param']

    return config_files

def default_scamp_config_files():
    '''Return a list of the needed files for SCAMP. The config file should be in
    element 0'''

    config_files = ['scamp_neox.cfg']

    return config_files

def default_sextractor_config_files(catalog_type='ASCII'):
    '''Return a list of the needed files for SExtractor. The config file should
    be in element 0'''

    common_config_files = ['gauss_1.5_3x3.conv', 'default.nnw']
    config_files = ['sextractor_neox.conf',
                    'sextractor_ascii.params']
    if catalog_type == 'FITS_LDAC':
        config_files = ['sextractor_neox_ldac.conf',
                        'sextractor_ldac.params']

    config_files = config_files + common_config_files
    return config_files

def setup_mtdlink_dir(source_dir, dest_dir):
    '''Setup a temporary working directory for running MTDLINK in <dest_dir>. The
    needed config files are symlinked from <source_dir>'''

    mtdlink_config_files = default_mtdlink_config_files()

    return_value = setup_working_dir(source_dir, dest_dir, mtdlink_config_files)

    return return_value

def setup_scamp_dir(source_dir, dest_dir):
    '''Setup a temporary working directory for running SCAMP in <dest_dir>. The
    needed config files are symlinked from <source_dir>'''

    scamp_config_files = default_scamp_config_files()

    return_value = setup_working_dir(source_dir, dest_dir, scamp_config_files)

    return return_value

def setup_sextractor_dir(source_dir, dest_dir, catalog_type='ASCII'):
    '''Setup a temporary working directory for running SExtractor in <dest_dir>.
    The needed config files are symlinked from <source_dir>'''

    sextractor_config_files = default_sextractor_config_files(catalog_type)

    return_value = setup_working_dir(source_dir, dest_dir, sextractor_config_files)

    return return_value

def setup_working_dir(source_dir, dest_dir, config_files):
    '''Sets up a temporary working directory for running programs in <dest_dir>.
    The temporary working directory is created if needed and the required config
    files (given in a list in <config_files>) are symlinked from <source_dir> if
    they don't already exist in <dest_dir>'''

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
                logger.warn("Could not unlink %s" % ( config_dest_filepath))
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
    '''Python equivalent of 'which' command to find a binary in the path (can
    also be given a specific pathname'''

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
            options += option_mapping[option] +' ' + str(header.get(header_mapping[option])) + ' '
    options = options.rstrip()
    return options

def determine_mtdlink_options(num_fits_files, param_file, pa_rate_dict):

    options = ''
    options += '-paramfile' + ' ' + str(param_file) + ' '
    options += '-CPUTIME' + ' ' + str(num_fits_files*200) + ' '
    options += '-MAXMISSES' + ' ' + str(int(floor(num_fits_files/2.5))) + ' '
    options += '-FILTER_PA' + ' ' + str(pa_rate_dict['filter_pa']) + ' '
    options += '-FILTER_DELTAPA' + ' ' + str(pa_rate_dict['filter_deltapa']) + ' '
    options += '-FILTER_MINRATE' + ' ' + str(pa_rate_dict['filter_minrate']) + ' '
    options += '-FILTER_MAXRATE' + ' ' + str(pa_rate_dict['filter_maxrate']) + ' '
    options = options.rstrip()
    return options

def determine_scamp_options(fits_catalog):

    options = ''

    return options

def add_l1filter(fits_file):
    '''Adds a L1FILTER keyword into the <fits_file> with the same value
    as FILTER. If not found, nothing is done.'''

    hdulist = fits.open(fits_file, mode='update')
    prihdr = hdulist[0].header
    filter_val = prihdr.get('FILTER', None)
    if filter_val:
        prihdr['L1FILTER'] = (filter_val, 'Copy of FILTER for SCAMP')
    hdulist.close()

    return

@timeit
def run_sextractor(source_dir, dest_dir, fits_file, binary=None, catalog_type='ASCII', dbg=False):
    '''Run SExtractor (using either the binary specified by [binary] or by
    looking for 'sex' in the PATH) on the passed <fits_file> with the results
    and any temporary files created in <dest_dir>. <source_dir> is the path
    to the required config files.'''

    status = setup_sextractor_dir(source_dir, dest_dir, catalog_type)
    if status != 0:
        return status

    binary = binary or find_binary("sex")
    if binary == None:
        logger.error("Could not locate 'sex' executable in PATH")
        return -42

    # If we are making FITS_LDAC catalogs for SCAMP, we need to create a new
    # header keyword of L1FILTER and set the value to FILTER. This prevents
    # SCAMP false matching on the first FITS keyword starting with FILTER
    if catalog_type == 'FITS_LDAC':
        add_l1filter(fits_file)

    sextractor_config_file = default_sextractor_config_files(catalog_type)[0]
    options = determine_sext_options(fits_file)
    cmdline = "%s %s -c %s %s" % ( binary, fits_file, sextractor_config_file, options )
    cmdline = cmdline.rstrip()

    if dbg == True:
        retcode_or_cmdline = cmdline
    else:
        logger.debug("cmdline=%s" % cmdline)
        args = cmdline.split()
        retcode_or_cmdline = call(args, cwd=dest_dir)

    return retcode_or_cmdline

@timeit
def run_scamp(source_dir, dest_dir, fits_catalog_path, binary=None, dbg=False):
    '''Run SCAMP (using either the binary specified by [binary] or by
    looking for 'scamp' in the PATH) on the passed <fits_catalog_path> with the
    results and any temporary files created in <dest_dir>. <source_dir> is the
    path to the required config files.'''

    status = setup_scamp_dir(source_dir, dest_dir)
    if status != 0:
        return status

    binary = binary or find_binary("scamp")
    if binary == None:
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
    cmdline = "%s %s -c %s %s" % ( binary, fits_catalog, scamp_config_file, options )
    cmdline = cmdline.rstrip()

    if dbg == True:
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
def run_mtdlink(source_dir, dest_dir, mtds_file_path, fits_files, num_fits_files, param_file, pa_rate_dict, binary=None, catalog_type='ASCII', dbg=False):
    '''Run MTDLINK (using either the binary specified by [binary] or by
    looking for 'mtdlink' in the PATH) on the passed <fits_files> with the results
    and any temporary files created in <dest_dir>. <source_dir> is the path
    to the required config files.'''

    status = setup_mtdlink_dir(source_dir, dest_dir)
    if status != 0:
        return status

    binary = binary or find_binary("mtdlink")
    if binary == None:
        logger.error("Could not locate 'mtdlink' executable in PATH")
        return -42

    mtdlink_config_file = default_mtdlink_config_files()[0]
    fits_file_list = fits_files.split(' ')
    first_fits_file = fits_file_list[0]
    options = determine_mtdlink_options(num_fits_files, param_file, pa_rate_dict)

    # MTDLINK requires an 'MJD' keyword to be in the header.
    # If one doesn't exist, copy 'MJD-OBS' to 'MJD'.
    y = 0
    for f in fits_file_list:
        if os.path.exists(f):
            data, header = fits.getdata(f, header=True)
            if 'MJD' not in header :
                mjd = header['MJD-OBS'] + (0.5*header['exptime']/86400.0)
                header.insert('MJD-OBS', ('MJD', mjd, '[UTC days] Start date/time (Modified Julian Dat'), after=True)
                fits.writeto(f, data, header, clobber=True, checksum=True)
        y += 1

    # MTDLINK writes the output header file to the path that the FITS files are in,
    # not to the directory MTDLINK is being run from...
    # If the fits_catalog has a path component, we symlink it to the directory.
    mtds_file = os.path.basename(mtds_file_path)
    if mtds_file != mtds_file_path:
        mtds_file = os.path.join(dest_dir, mtds_file)
        # If the file exists and is a link (or a broken link), then remove it
        if os.path.lexists(mtds_file) and os.path.islink(mtds_file):
            os.unlink(mtds_file)
        os.symlink(mtds_file_path, mtds_file)

    # MTDLINK wants the input fits files to be in the directory MTDLINK is
    # being run from...
    # If the fits files have a path component, we symlink them to the directory.
    symlink_fits_files = []
    y = 0
    for f in fits_file_list:
        fits_file = os.path.basename(fits_file_list[y])
        if fits_file != fits_file_list[y]:
            fits_file = os.path.join(dest_dir, fits_file)
            # If the file exists and is a link (or a broken link), then remove it
            if os.path.lexists(fits_file) and os.path.islink(fits_file):
                os.unlink(fits_file)
            os.symlink(fits_file_list[y], fits_file)
        symlink_fits_files.append(fits_file)
        y += 1

    # MTDLINK wants the input sext files to be in the directory MTDLINK is
    # being run from...
    # If the sext files have a path component, we symlink them to the directory.
    fits_file_list = fits_files.split(' ')
    symlink_sext_files = []
    y = 0
    for f in fits_file_list:
        sext_file = os.path.basename(fits_file_list[y].replace('fits', 'sext'))
        if sext_file != fits_file_list[y].replace('fits', 'sext'):
            sext_file = os.path.join(dest_dir, sext_file)
            # If the file exists and is a link (or a broken link), then remove it
            if os.path.lexists(sext_file) and os.path.islink(sext_file):
                os.unlink(sext_file)
            os.symlink(fits_file_list[y].replace('fits', 'sext'), sext_file)
        symlink_sext_files.append(sext_file)
        y += 1

    linked_fits_files = ' '.join(symlink_fits_files)

    cmdline = "%s %s %s %s %s" % ( 'time', binary, '-verbose', options, linked_fits_files )
    cmdline = cmdline.rstrip()
    print cmdline

    if dbg == True:
        retcode_or_cmdline = cmdline
    else:
        logger.debug("cmdline=%s" % cmdline)
        args = cmdline.split()
#        retcode_or_cmdline = call(args, cwd=dest_dir)
        # Open mtdlink_output.out for writing the MTDLINK output into
        output_file = open(os.path.join(dest_dir, 'mtdlink_output.out'), 'w')
        retcode_or_cmdline = call(args, cwd=dest_dir, stdout=output_file, stderr=output_file)
        output_file.close()

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
    reference_catalog = reference_catalog.replace('-', '')
    info = { 'num_match'    : fgroups_table.array['AstromNDets_Internal_HighSN'].data[0],
             'num_refstars' : fields_table.array['NDetect'].data[0],
             'wcs_refcat'   : "<Vizier/aserver.cgi?%s@cds>" % reference_catalog.lower(),
             'wcs_cattype'  : "%s@CDS" % reference_catalog.upper(),
             'wcs_imagecat' : fields_table.array['Catalog_Name'].data[0],
             'pixel_scale'  : fields_table.array['Pixel_Scale'].data[0].mean()
           }

    return info

def updateFITSWCS(fits_file, scamp_file, scamp_xml_file, fits_file_output):
    '''Update the WCS information in a fits file with a bad WCS solution
    using the SCAMP generated FITS-like .head ascii file.
    <fits_file> should the processed CCD image to update, <scamp_file> is
    the SCAMP-produced .head file, <scamp_xml_file> is the SCAMP-produced
    XML output file and <fits_file_output> is the new output FITS file.'''

    try:
        data, header = fits.getdata(fits_file, header=True)
    except IOError as e:
        logger.error("Unable to open FITS image %s (Reason=%s)" % (fits_file, e))
        return -1

    scamp_info = get_scamp_xml_info(scamp_xml_file)
    if scamp_info == None:
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
            astirms1 = round(float(line[9:31]),7)
        if 'ASTIRMS2' in line:
            astirms2 = round(float(line[9:31]),7)
        if 'ASTRRMS1' in line:
            astrrms1 = round(float(line[9:31])*3600.0,5)
        if 'ASTRRMS2' in line:
            astrrms2 = round(float(line[9:31])*3600.0,5)
    scamp_head_fh.close()

    #update from scamp xml VOTable
    wcsrfcat = scamp_info['wcs_refcat']
    wcsimcat = scamp_info['wcs_imagecat']
    wcsnref = scamp_info['num_refstars']
    wcsmatch = scamp_info['num_match']
    wccattyp = scamp_info['wcs_cattype']
    secpix = round(scamp_info['pixel_scale'],6)

    #header keywords we have
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

    #header keywords we (probably) don't have. Insert after CTYPE2
    if header.get('CUNIT1', None) == None:
        header.insert('CTYPE2', ('CUNIT1', cunit1, 'Unit of 1st axis'), after=True)
    if header.get('CUNIT2', None) == None:
        header.insert('CUNIT1', ('CUNIT2', cunit2, 'Unit of 2nd axis'), after=True)

    # Need to force the CHECKSUM to be recomputed. Trap for young players..
    fits.writeto(fits_file_output, data, header, clobber=True, checksum=True)

    return 0
