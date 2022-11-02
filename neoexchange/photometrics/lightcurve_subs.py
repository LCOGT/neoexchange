"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2021-2021 LCO

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
import re
import warnings

import numpy as np
from astropy.time import Time
from astropy.wcs import FITSFixedWarning
from astropy.table import Table, unique, Column
from core.models import Frame, CatalogSources, SourceMeasurement

import logging

logger = logging.getLogger(__name__)

def read_photompipe_file(filepath):
    """Reads a photometry table file at <filepath> produced by the photometrypipeline and
    returns an Astropy Table.
    """

    table = None
    if os.path.exists(filepath):
        table = Table.read(filepath, format='ascii.commented_header')
        if len(table) >= 2:
            if table['filename'][0] == table['filename'][1]:
                logger.debug("Doubling detected")
                table = unique(table, keys='filename')
    return table

def extract_photompipe_aperradius(logfile):
    """Parse through a passed photometrypipeline log file to extract the
    aperture radius used.
    """

    aper_radius = None

    if os.path.exists(logfile):
        regex = r"aperture radius: (\d+.\d+)"
        with open(logfile, 'r') as f:
            for line in f.readlines():
                matches = re.search(regex, line)
                if matches:
                    if len(matches.groups()) == 1:
                        aper_radius = float(matches.group(1))
                    else:
                        logger.warning("Unexpected number of matches")
            if aper_radius is None:
                logger.info("Not found, trying alternative method")
                f.seek(0)
                regex = r"^pp_extract.*'aprad': (\d+.\d+)"
                for line in f.readlines():
                    matches = re.search(regex, line)
                    if matches:
                        if len(matches.groups()) == 1:
                            aper_radius = float(matches.group(1))
                        else:
                            logger.warning("Unexpected number of matches")
    return aper_radius

def create_table_from_srcmeasures(block):
    """Creates an AstroPy table (of the format suitable for write_dartformat_file()) from
    the SourceMeasurements associated with Block <block>"""

    col_names = ['filename', 'julian_date', 'mag', 'sig', 'ZP', 'ZP_sig', 'inst_mag', 'in_sig', '[7]', '[8]', 'aprad']
    dtypes = ('<U36', '<f8', '<f8', '<f8', '<f8', '<f8', '<f8', '<f8', '<U7', '<i8', '<f8')
    table = Table(names=col_names, dtype=dtypes)

    sources = SourceMeasurement.objects.filter(frame__block=block, frame__frametype=Frame.NEOX_RED_FRAMETYPE).order_by('frame__midpoint')

    warnings.simplefilter('ignore', FITSFixedWarning)

    tolerance = 0.5 / 3600.0
    mag_tolerance = 0.01
    for i, src in enumerate(sources):
        t = Time(src.frame.midpoint)
        catsrc = CatalogSources.objects.filter(frame=src.frame, obs_ra__range=(src.obs_ra-tolerance, src.obs_ra+tolerance),\
            obs_dec__range=(src.obs_dec-tolerance, src.obs_dec+tolerance),\
            obs_mag__range=(src.obs_mag-mag_tolerance, src.obs_mag+mag_tolerance))
        flags = 0
        if catsrc.count() == 1:
            flags = catsrc[0].flags
        else:
            logger.warning(f"Unexpected number of CatalogSources ({catsrc.count()}) found for {src.frame.filename}")
        # print(i, src.frame.filename, t.jd, src.obs_mag, src.err_obs_mag,
               # src.frame.zeropoint,\
               # src.frame.zeropoint_err,\
               # src.obs_mag-src.frame.zeropoint,\
               # src.err_obs_mag,\
               # flags, src.aperture_size)
        row = [src.frame.filename, t.jd, src.obs_mag, \
               np.sqrt(src.err_obs_mag**2 + src.frame.zeropoint_err**2),
               src.frame.zeropoint,\
               src.frame.zeropoint_err,\
               src.obs_mag-src.frame.zeropoint,\
               src.err_obs_mag,\
               src.frame.filter,
               flags, src.aperture_size_pixels]
        table.add_row(row)

    return table

def write_dartformat_file(table, filepath, aprad=0.0):
    """Writes out the passed Astropy <table > in "DART lightcurve format" to the
    given <filepath>"""

    output_col_names = ['file', 'julian_date', 'mag', 'sig', 'ZP', 'ZP_sig', 'inst_mag', 'inst_sig', 'filter', 'SExtractor_flag', 'aprad']
    input_col_names = ['filename', 'julian_date', 'mag', 'sig', 'ZP', 'ZP_sig', 'inst_mag', 'in_sig', '[7]', '[8]', 'aprad']
    def_fmt = '%.4f'
    formatters = {  'file' : '%-36.36s', 'julian_date' : '%15.7f', 'mag' : def_fmt, 'sig' : def_fmt,
                    'ZP' : def_fmt, 'ZP_sig' : def_fmt, 'inst_mag' : def_fmt, 'inst_sig' : def_fmt,
                    'aprad' : '%.2f'
                 }

    # Create directory path if it doesn't exist
    filepath_dir = os.path.dirname(filepath)
    if os.path.exists(filepath_dir) is False:
        os.makedirs(filepath_dir)

    # Replace truncated '.lda' in filename with real name.
    # Also add a column for aperture radius
    new_names = [x.replace('.lda','.fits').replace('e91','e92') for x in table['filename']]
    table.replace_column('filename', new_names)
    if 'aprad' not in table.colnames:
        aprad_column = Column(np.full(len(table), aprad), name='aprad')
        table.add_column(aprad_column)
    table[input_col_names].write(filepath, format='ascii.fixed_width', names=output_col_names,
        comment=False, delimiter='', formats=formatters)

    return

def write_photompipe_file(table, filepath):
    """Writes out the passed Astropy <table > in "photometrypipeline lightcurve format" to the
    given <filepath>"""
    with open(filepath,  'w') as out_fh:
        # Write header
        out_fh.write('#                           filename     julian_date      ' +
                   'mag    sig     source_ra    source_dec   [1]   [2]   ' +
                   '[3]   [4]    [5]       ZP ZP_sig inst_mag ' +
                   'in_sig               [6] [7] [8]    [9]          [10] ' +
                   'FWHM"\n')

        # Iterate over rows
        for row in table:
            out_fh.write(('%35.35s ' % row['filename'].replace(' ', '_')) +
                       ('%15.7f ' % row['julian_date']) +
                       ('%8.4f ' % row['mag']) +
                       ('%6.4f ' % row['sig']) +
                       ('%13.8f ' % row['source_ra']) +
                       ('%+13.8f ' % row['source_dec']) +
                       ('%5.2f ' % row['[1]']) +
                       ('%5.2f ' % row['[2]']) +
                       ('%5.2f ' % row['[3]']) +
                       ('%5.2f ' % row['[4]']) +
                       ('%5.2f ' % row['[5]']) +
                       ('%8.4f ' % row['ZP']) +
                       ('%6.4f ' % row['ZP_sig']) +
                       ('%8.4f ' % row['inst_mag']) +
                       ('%6.4f ' % row['in_sig']) +
                       ('%s ' % row['[6]']) +
                       ('%s ' % row['[7]']) +
                       ('%3d ' % row['[8]']) +
                       ('%s' % row['[9]']) +
                       ('%10s ' % row['[10]']) +
                       ('%4.2f\n' % row['FWHM"']))

        # Write footer
        out_fh.writelines('#\n# [1]: predicted_RA - source_RA [arcsec]\n' +
                        '# [2]: predicted_Dec - source_Dec [arcsec]\n' +
                        '# [3,4]: manual target offsets in RA and DEC ' +
                        '[arcsec]\n' +
                        '# [5]: exposure time (s)\n' +
                        '# [6]: photometric catalog\n' +
                        '# [7]: photometric band\n' +
                        '# [8]: Source Extractor flag\n' +
                        '# [9]: telescope/instrument\n' +
                        '# [10]: photometry method\n')
    return
