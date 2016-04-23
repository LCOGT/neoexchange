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
from subprocess import call
from collections import OrderedDict
import warnings

from astropy.io import fits
from astropy.io.votable import parse

from photometrics.catalog_subs import oracdr_catalog_mapping

logger = logging.getLogger(__name__)

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

def determine_options(fits_file):

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

def determine_scamp_options(fits_catalog):

    options = ''

    return options

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

    sextractor_config_file = default_sextractor_config_files(catalog_type)[0]
    options = determine_options(fits_file)
    cmdline = "%s %s -c %s %s" % ( binary, fits_file, sextractor_config_file, options )
    cmdline = cmdline.rstrip()

    if dbg == True:
        retcode_or_cmdline = cmdline
    else:
        logger.debug("cmdline=%s" % cmdline)
        args = cmdline.split()
        retcode_or_cmdline = call(args, cwd=dest_dir)

    return retcode_or_cmdline

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
        retcode_or_cmdline = call(args, cwd=dest_dir)

    return retcode_or_cmdline

def get_scamp_xml_info(scamp_xml_file):

    # SCAMP VOTable's are malformed and will throw an astropy W42 warning which
    # we don't want. Wrap in context manager to get rid of this
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        votable = parse(scamp_xml_file)

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
           }

    return info

def updateFITSWCS(fits_file, scamp_file):
    '''Update the WCS information in a fits file with a bad WCS solution
    using the SCAMP generated FITS-like .head ascii file.'''

    fits_file_output = os.path.abspath(os.path.join('photometrics', 'tests', 'example-sbig-e10_output.fits'))

    data, header = fits.getdata(fits_file, header=True)

    for i in range(1, 100):
        line = scamp_file.readline()
        if 'HISTORY' in line:
            wcssolvr = str(line[34:39]+'-'+line[48:53])
        if 'CUNIT1' in line:
            cunit1 = line[9:31]
        if 'CUNIT2' in line:
            cunit2 = line[9:31]
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
            astrrms1 = round(float(line[9:31]),7)
        if 'ASTRRMS2' in line:
            astrrms2 = round(float(line[9:31]),7)

    #need to figure out how to get these values out of scamp standard output
    wcsrfcat = 'null'
    wcsimcat = 'null'
    wcsnref = int(0)
    wcsmatch = int(0)
    wccattyp = 'null'

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
    header['WCSSOLVR'] = wcssolvr
    header['WCSRFCAT'] = wcsrfcat
    header['WCSIMCAT'] = wcsimcat
    header['WCSNREF'] = wcsnref
    header['WCSMATCH'] = wcsmatch
    header['WCCATTYP'] = wccattyp
    header['WCSRDRES'] = str(str(astrrms1)+'/'+str(astrrms2))
    header['WCSERR'] = 0

    #header keywords we don't have
    header['CUNIT1'] = cunit1
    header['CUNIT2'] = cunit2

    fits.writeto(fits_file_output, data, header, clobber=True)

    return fits_file, fits_file_output, scamp_file
