"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2021-2022 LCO

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
from collections import OrderedDict

import numpy as np
from astropy.time import Time
from astropy.table import Table, unique, Column
import logging

logger = logging.getLogger(__name__)

def read_neoxpipe_file(filepath):
    """Reads a photometry file at <filepath> produced by NEOexchange's lightcurve_extraction
    and returns an Astropy Table.
    """

    table = None

    tbl_mapping = OrderedDict([
                    ('mag', 'Mag'),
                    ('sig', 'Mag_error'), 
                    ('in_sig', 'Int_error'),
                    ('ZP_sig', 'ZP_error')
                    ])
    if os.path.exists(filepath):
        table = Table.read(filepath, format='ascii.commented_header', header_start=1)
        # Rename columns
        for new_name in tbl_mapping:
            table.rename_column(tbl_mapping[new_name], new_name)
        # Convert first column from a truncated MJD to a full JD
        mjd_offset = float(table.colnames[0].split('-')[1])
        times = Time(table.columns[0]+mjd_offset, format='mjd', scale='utc')
        new_times = Column(times.jd, 'julian_date')
        table.add_column(new_times, 0)
    return table

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

def write_dartformat_file(table, filepath, aprad=0.0):
    """Writes out the passed Astropy <table > in "DART lightcurve format" to the
    given <filepath>"""

    output_col_names = ['file', 'julian_date', 'mag', 'sig', 'ZP', 'ZP_sig', 'inst_mag', 'inst_sig', 'SExtractor_flag', 'aprad']
    input_col_names = ['filename', 'julian_date', 'mag', 'sig', 'ZP', 'ZP_sig', 'inst_mag', 'in_sig', '[8]', 'aprad']
    col_starts = [0, 37, 53, 61, 68, 76, 83, 92, 99, 115]
    def_fmt = '%.4f'
    formatters = {  'julian_date' : '%15.7f', 'mag' : def_fmt, 'sig' : def_fmt,
                    'ZP' : def_fmt, 'ZP_sig' : def_fmt, 'inst_mag' : def_fmt, 'inst_sig' : def_fmt,
                    'aprad' : '%.2f'
                 }

    # Replace truncated '.lda' in filename with real name.
    # Also add a column for aperture radius
    new_names = [x.replace('.lda','.fits') for x in table['filename']]
    table.replace_column('filename', new_names)
    aprad_column = Column(np.full(len(table), aprad), name='aprad')
    table.add_column(aprad_column)
    table[input_col_names].write(filepath, format='ascii.fixed_width', names=output_col_names,
        col_starts=col_starts, comment=False, delimiter='', formats=formatters)

    return

def split_filename(filename):
    """Splits an LCO filename <filename> into component parts
    Returns a dict of components"""

    name_parts = {}
    fileroot, name_parts['extension'] = os.path.splitext(filename)
    if len(fileroot) >= 31:
        chunks = fileroot.split('-')
        name_parts['site'] = chunks[0][0:3]
        name_parts['tel_class'] = chunks[0][3:6]
        name_parts['tel_serial'] = chunks[0][6:8]
        name_parts['instrument'] = chunks[1]
        name_parts['dayobs'] = chunks[2]
        name_parts['frame_num'] = chunks[3]
        name_parts['frame_type'] = chunks[4]

    return name_parts
