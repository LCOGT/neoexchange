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

from astropy.io import fits

from photometrics.catalog_subs import oracdr_catalog_mapping

logger = logging.getLogger(__name__)

def default_scamp_config_files():
    '''Return a list of the needed files for SCAMP. The config file should be in
    element 0'''

    config_files = ['scamp_neox.cfg']

    return config_files

def default_sextractor_config_files():
    '''Return a list of the needed files for SExtractor. The config file should
    be in element 0'''

    config_files = ['sextractor_neox.conf',
                    'sextractor_ascii.params',
                    'gauss_1.5_3x3.conv', 'default.nnw']

    return config_files

def setup_scamp_dir(source_dir, dest_dir):
    '''Setup a temporary working directory for running SCAMP in <dest_dir>. The
    needed config files are symlinked from <source_dir>'''

    scamp_config_files = default_scamp_config_files()

    return_value = setup_working_dir(source_dir, dest_dir, scamp_config_files)

    return return_value

def setup_sextractor_dir(source_dir, dest_dir):
    '''Setup a temporary working directory for running SExtractor in <dest_dir>.
    The needed config files are symlinked from <source_dir>'''

    sextractor_config_files = default_sextractor_config_files()

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
        if os.path.exists(config_dest_filepath):
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

def run_sextractor(source_dir, dest_dir, fits_file, binary=None, dbg=False):
    '''Run SExtractor (using either the binary specified by [binary] or by
    looking for 'sex' in the PATH) on the passed <fits_file> with the results
    and any temporary files created in <dest_dir>. <source_dir> is the path
    to the required config files.'''

    status = setup_sextractor_dir(source_dir, dest_dir)
    if status != 0:
        return status

    binary = binary or find_binary("sex")
    if binary == None:
        logger.error("Could not locate 'sex' executable in PATH")
        return -42

    sextractor_config_file = default_sextractor_config_files()[0]
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
