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

import numpy as np
from astropy.time import Time
from astropy.table import Table, unique, Column
from core.models import Frame, SourceMeasurement

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
    return aper_radius

def create_table_from_srcmeasures(block):
    """Creates an AstroPy table (of the format suitable for write_dartformat_file()) from
    the SourceMeasurements associated with Block <block>"""

    col_names = ['filename', 'julian_date', 'mag', 'sig', 'ZP', 'ZP_sig', 'inst_mag', 'in_sig', '[8]', 'aprad']
    dtypes = ('<U36', '<f8', '<f8', '<f8', '<f8', '<f8', '<f8', '<f8', '<i8', '<f8')
    table = Table(names=col_names, dtype=dtypes)

    sources = SourceMeasurement.objects.filter(frame__block=block, frame__frametype=Frame.BANZAI_RED_FRAMETYPE)

    for src in sources:
        t = Time(src.frame.midpoint)
        # XXX map back to original CatalogSource
        flags = 0
        row = [src.frame.filename, t.jd, src.obs_mag, src.err_obs_mag,
               src.frame.zeropoint, src.frame.zeropoint_err, src.obs_mag, src.err_obs_mag,
               flags, src.aperture_size]
        table.add_row(row)

    return table

def write_dartformat_file(table, filepath, aprad=0.0):
    """Writes out the passed Astropy <table > in "DART lightcurve format" to the
    given <filepath>"""

    output_col_names = ['file', 'julian_date', 'mag', 'sig', 'ZP', 'ZP_sig', 'inst_mag', 'inst_sig', 'SExtractor_flag', 'aprad']
    input_col_names = ['filename', 'julian_date', 'mag', 'sig', 'ZP', 'ZP_sig', 'inst_mag', 'in_sig', '[8]', 'aprad']
    col_starts = [0, 37, 53, 61, 68, 76, 83, 92, 99, 115]
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
    new_names = [x.replace('.lda','.fits') for x in table['filename']]
    table.replace_column('filename', new_names)
    aprad_column = Column(np.full(len(table), aprad), name='aprad')
    table.add_column(aprad_column)
    table[input_col_names].write(filepath, format='ascii.fixed_width', names=output_col_names,
        comment=False, delimiter='', formats=formatters)

    return
