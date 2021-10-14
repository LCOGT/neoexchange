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

from astropy.table import Table, unique

def read_photompipe_file(filepath):
    """Reads a photometry table file at <filepath> produced by the photometrypipeline and
    returns an Astropy Table.
    """

    table = None
    if os.path.exists(filepath):
        table = Table.read(filepath, format='ascii.commented_header')
        if len(table) >= 2:
            if table['filename'][0] == table['filename'][1]:
                print("Doubling detected")
                table = unique(table, keys='filename')
    return table

def write_dartformat_file(table, filepath):
    """Writes out the passed Astropy <table > in "DART lightcurve format" to the
    given <filepath>"""

    output_col_names = ['file', 'julian_date', 'mag', 'sig', 'ZP', 'ZP_sig', 'inst_mag', 'inst_sig', 'SExtractor_flag', 'aprad']
    input_col_names = ['filename', 'julian_date', 'mag', 'sig', 'ZP', 'ZP_sig', 'inst_mag', 'in_sig', '[8]', 'FWHM"']
    col_starts = [0, 37, 53, 61, 68, 76, 83, 92, 99, 115]

    table[input_col_names].write(filepath, format='ascii.fixed_width', names=output_col_names, col_starts=col_starts, comment=False, delimiter='')

    return
