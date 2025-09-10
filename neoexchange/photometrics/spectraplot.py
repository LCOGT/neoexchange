"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2018-2019 LCO

convert 1D fits spectra into a readable plot

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from astropy.io import fits, ascii
from astropy.convolution import convolve
from astropy.wcs import WCS
from astropy import units as u
from datetime import datetime

import os
import logging
import numpy as np
import warnings
import re
import urllib
import csv
from scipy import interpolate

from django.conf import settings
from django.core.files.storage import default_storage
from core.utils import search

logger = logging.getLogger(__name__)


def get_x_units(x_data):
    """finds wavelength units from x_data
       inputs: <xdata>: unitless wavelength data
       outputs: wavelength in Angstroms
    """
    x_mean = np.mean(x_data)

    # assuming visible to NIR range (~3000-10000A)
    if x_mean > 1000:
        x_units = u.AA  # (Angstroms)
    elif 100 < x_mean < 1000:
        x_units = u.nm
    elif .1 < x_mean < 10:
        x_units = u.micron
    else:
        logger.warning("Could not parse wavelength units from file. Assuming Angstoms")
        x_units = u.AA
    xxx = np.array(x_data)
    wavelength = (xxx * x_units).to(u.AA)
    return wavelength


def get_y_units(y_data, filename, y_error=[]):
    """finds flux/reflectance units
       inputs: y_data, spectrum file
       outputs: scaled flux with Units
    """
    y_factor = 1
    if "ctiostan" in filename and '.dat' in filename:  # from ESO aaareadme.ctio
        y_units = u.erg/(u.cm**2)/u.s/u.AA
        y_factor = 10**16

    elif .001 < np.median(y_data) < 10:  # Probably Normalized
        y_units = u.def_unit("Normalized_Reflectance", u.dimensionless_unscaled)

    elif '_2df_ex.fits' in filename:  # from FLOYDS-IRAF
        y_factor = 10**20
        y_units = u.erg/(u.cm**2)/u.s/u.AA

    elif '-1d.fits' in filename:  # from FLOYDS-BANZAI
        y_factor = 1
        y_units = u.erg/(u.cm**2)/u.s/u.AA

    else:
        logger.warning("Could not parse flux units from file. Assuming erg/cm^2/s/A")
        y_units = u.erg/(u.cm**2)/u.s/u.AA

    yyy = np.array(y_data)
    err = np.array(y_error)
    flux = ((yyy / y_factor) * y_units)
    error = ((err / y_factor) * y_units)
    return flux, error


def pull_data_from_text(spectra):
    """Pull spectroscopy data from text file.
        Assume 1st column = wavelength
        Assume 2nd column = flux or reflectance
        assume 3rd column = error (even though not the case in standard stars)
        Return wavelength in Angstroms, flux, and error with units."""
    if default_storage.exists(spectra):
        with default_storage.open(spectra, mode='rb') as f:
            lines = f.read()
    else:
        try:
            with urllib.request.urlopen(spectra) as f:
                lines = f.read()
        except ValueError:
            return [], [], []
        except urllib.request.URLError:
            logger.error(f"Connection to {spectra} error")
            return [], [], []
    lines = re.split('[\n\r]', str(lines, 'utf-8'))
    xxx = []
    yyy = []
    err = []
    for line in lines:
        try:
            chunks = line.split(' ')
            chunks = list(filter(None, chunks))
            if len(chunks) >= 2:
                if float(chunks[1]) != -1:
                    xxx.append(float(chunks[0]))
                    yyy.append(float(chunks[1]))
                    if len(chunks) >= 3:
                        err.append(float(chunks[2]))
        except ValueError:
            continue

    wavelength = get_x_units(xxx)
    flux, err = get_y_units(yyy, spectra, err)
    return wavelength, flux, err


def pull_data_from_spectrum(spectra):
    """Extract spectroscopy data from fits files.
        Return wavelength in Angstroms, flux with units.
        Return Header."""
    try:
        file = default_storage.open(spectra)
        hdul = fits.open(file)
    except FileNotFoundError as e:
        logger.warning(e)
        return None, None, None, None

    if len(hdul) == 1:
        # Old style FLOYDS
        data = hdul[0].data
        hdr = hdul[0].header

        yyy = data[0][0]
        err = data[3][0]
        w = WCS(hdr, naxis=1, relax=False, fix=False)
        lam = w.wcs_pix2world(np.arange(len(yyy)), 0)[0]
    elif len(hdul) == 5:
        # New style FLOYDS-BANZAI
        banzai_spectrum = hdul['SPECTRUM'].data
        hdr = hdul['PRIMARY'].header

        yyy = banzai_spectrum['flux']
        err = banzai_spectrum['fluxerror']
        lam = banzai_spectrum['wavelength']


    wavelength = get_x_units(lam)
    flux, error = get_y_units(yyy, spectra, err)
    return wavelength, flux, hdr, error


def read_mean_tax():
    """Read in the BusDeMeo Mean standard taxonomies and errors.
        Return dictionary of flux/error for all taxonomies"""
    mean_spec_file = os.path.join(settings.BASE_DIR, 'photometrics', 'data', 'busdemeo-meanspectra.csv')
    with open(mean_spec_file, newline='') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        spec_dict = {}
        for row in csv_reader:
            if line_count == 1:
                header = row
                for head in header:
                    spec_dict[head] = []
                line_count += 1
            elif line_count > 1:
                for i, r in enumerate(row):
                    spec_dict[header[i]].append(float(r))
                line_count += 1
            else:
                line_count += 1
    return spec_dict


def spectrum_plot(spectra, data_set='', analog=None, offset=0):
    """Sets up X/Y plottable data from spectroscopic input.
        Creates Reflectance Spectra if analog given.
        Otherwise clips and normalizes spectrum.
        input:
            spectra: The input spectrum (path to fits file)
            data_set: A Name, Title, or Description of the data
            analog: The input comparison spectrum (path to fits file
            offset: interger used as a linear offest for the y values of the final result. Useful for spreading out
             multiple datasets to be plotted on the same plot. (physical offset = 0.2*X where X is int given here.)
        Returns:
            data_set: data label
            y_clipped: normalized and truncated flux/reflectance values
            x_clipped: truncated wavelength values"""

    windows = ['flat', 'hanning', 'hamming', 'bartlett', 'blackman']
    spec_x, spec_y, spec_header, spec_error = pull_data_from_spectrum(spectra)
    if spec_y is None:
        return data_set, None, None, None

    box = 100
    if analog:
        analog_x, analog_y, analog_header, analog_error = pull_data_from_spectrum(analog)
        if analog_y is None:
            yyy = spec_y
            yerr = spec_error
            analog = None
        else:
            spec_y_sm = smooth(spec_y, box, windows[1])
            spec_er_sm = smooth(spec_error, box, windows[1])
            analog_y_sm = smooth(analog_y, box, windows[1])
            analog_er_sm = smooth(analog_error, box, windows[1])
            interpolation_function = interpolate.interp1d(analog_x, analog_y_sm, kind='cubic', fill_value='extrapolate')
            err_interp_function = interpolate.interp1d(analog_x, analog_er_sm, kind='cubic', fill_value='extrapolate')
            shifted_analog_flux = interpolation_function(spec_x)
            shifted_analog_err = err_interp_function(spec_x)
            yyy = spec_y_sm / shifted_analog_flux
            yerr = np.sqrt((spec_er_sm / spec_y_sm) ** 2 + (shifted_analog_err / shifted_analog_flux) ** 2) * abs(yyy)
    else:
        yyy = spec_y
        yerr = spec_error

    if not data_set:
        if spec_header['ROTMODE'].upper() == 'VFLOAT':
            slit_fig = '|'
        else:
            slit_fig = '/'
        if spec_header['APERWID'] == 6.0:
            slit_fig += slit_fig
        if analog:
            data_set = "{} -- {} -- {}".format(spec_header['OBJECT'], analog_header['OBJECT'], spec_header['DAY-OBS'])
        else:
            data_set = "{} -- {} ({}) [ {} ]".format(spec_header['OBJECT'], spec_header['DAY-OBS'],
                                                     round(spec_header['AIRMASS'], 3), slit_fig)
    elif data_set.upper() == 'NONE':
        data_set = ''

    xxx = spec_x

    smoothy = yyy

    upper_wav = 10000*u.AA
    if analog:
        lower_wave = 4000*u.AA
    else:
        lower_wave = 3100*u.AA

    # clip ends off spectrum
    y_clipped = np.take(smoothy, np.argwhere((lower_wave < xxx) & (xxx < upper_wav)).flatten())
    x_clipped = np.take(xxx, np.argwhere((lower_wave < xxx) & (xxx < upper_wav)).flatten())
    err_clipped = np.take(yerr, np.argwhere((lower_wave < xxx) & (xxx < upper_wav)).flatten())

    # normalize to 5500 Angstroms
    find_g = np.take(smoothy, np.argwhere((5400*u.AA < xxx) & (xxx < 5600*u.AA)).flatten())
    y_norm = y_clipped / np.mean(find_g)
    err_norm = err_clipped / np.mean(find_g)
    y_norm += 0.2*offset

    return data_set, y_norm, x_clipped, err_norm


def smooth(x, window_len=11, window='hanning'):
    """smooth the data using a window with requested size.

    This method is based on the convolution of a scaled window with the signal.
    The signal is prepared by introducing reflected copies of the signal
    (with the window size) in both ends so that transient parts are minimized
    in the begining and end part of the output signal.

    input:
        x: the input signal
        window_len: the dimension of the smoothing window; should be an odd integer
        window: the type of window from 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'
            flat window will produce a moving average smoothing.

    output:
        the smoothed signal

    example:
        t=linspace(-2,2,0.1)
        x=sin(t)+randn(len(t))*0.1
        y=smooth(x)

    see also:
        numpy.hanning, numpy.hamming, numpy.bartlett, numpy.blackman, numpy.convolve
        scipy.signal.lfilter

    TODO: the window parameter could be the window itself if an array instead of a string
    NOTE: length(output) != length(input), to correct this: return y[(window_len/2-1):-(window_len/2)] instead of just y.
    """

    if len(x) < window_len:
        raise ValueError("Input vector needs to be bigger than window size.")

    if window_len < 3:
        return x

    if window_len % 2 != 0:
        window_len += 1

    if window not in ['flat', 'hanning', 'hamming', 'bartlett', 'blackman']:
        raise ValueError("Window is on of 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'")

    s = np.r_[x[window_len - 1:0:-1], x, x[-2:-window_len - 1:-1]]

    if window == 'flat':  # moving average
        w = np.ones(window_len, 'd')
    else:
        w = eval('np.' + window + '(window_len)')

    y = np.convolve(w / w.sum(), s, mode='valid')

    return y[(window_len // 2 - 1):-(window_len // 2)]


# def read_spectra(path, spectra):
#     """reads in all important data from spectra file (Works for .ascii 2 .fits standards, and .txt)
#        inputs: <spectra_file>: path and file name to spectra
#        outputs: wavelength (Quantity type), flux, flux_error, x_units, y_units, obj_name
#     """
#     spectra_file = os.path.join(path, spectra)
#     other = None
#     if spectra_file.endswith('.fits'):
#         with fits.open(spectra_file, ignore_missing_end=True) as hdul:  # read in data
#             # LCO fits standard:
#             if hdul[0].data is not None:
#                 data = hdul[0].data
#                 hdr = hdul[0].header
#                 y_data = data.flatten()[:max(data.shape)]
#                 w = WCS(hdr, naxis=1, relax=False, fix=False)
#
#                 x_data = w.wcs_pix2world(np.arange(len(y_data)), 0)[0]
#
#                 try:
#                     flux_error = np.array(data[3][0])
#                 except IndexError:
#                     logger.warning("Could not parse error data for spectra")
#                     flux_error = np.zeros(len(x_data))
#             # fits standard 2:
#             elif hdul[1].data is not None:
#                 data = hdul[1].data
#                 hdr = hdul[1].header
#                 x_data = np.array(list(n[0] for n in data))
#                 y_data = np.array(list(n[1] for n in data))
#
#                 if len(data[0]) > 2:
#                     flux_error = np.array(list(n[2] for n in data))
#                 else:
#                     flux_error = np.zeros(len(x_data))
#             else:
#                 raise ImportError("Could not read data from .fits file")
#
#             try:
#                 obj_name = hdr['OBJECT']
#             except KeyError:
#                 obj_name = ''
#             try:
#                 tn = hdr['TRACKNUM'].lstrip('0')
#                 site = hdr['SITEID'].upper()
#                 rn = hdr['REQNUM'].lstrip('0')
#             except KeyError:
#                 tn = site = inst = None
#             try:
#                 date_obs = hdr['DATE-OBS']
#             except KeyError:
#                 date_obs = hdr['DATE_OBS']
#             date = datetime.strptime(date_obs, '%Y-%m-%dT%H:%M:%S.%f')
#             other = [date, tn, site, rn]
#             x_units = get_x_units(x_data)
#             y_units, y_factor = get_y_units(hdr)
#             check_norm(hdul[0].header.values())  # check if data is already normalized
#
#     elif spectra_file.endswith('.ascii'):
#         data = ascii.read(spectra_file)  # read in data
#         # assuming 3 columns: wavelength, flux/reflectance, error
#         columns = data.keys()
#         x_data = data[columns[0]]  # converting tables to ndarrays
#         y_data = data[columns[1]]
#         flux_error = data[columns[2]]
#         x_units = get_x_units(x_data)
#         y_units, y_factor = get_y_units(data.meta)
#         obj_name = ""  # No way to read object name from ascii files right now.
#
#     elif spectra_file.endswith('.dat'):  # assuming origin is ESO spec standards
#         data = open(spectra_file)  # read in data
#         filename = search(path, '.*.readme.ctio')
#         try:
#             ctio = next(filename)
#             ctiodata = default_storage.open(ctio, 'r').readlines()
#             x_data = np.array([])
#             y_data = np.array([])
#             flux_error = np.array([])
#             for line in data:
#                 x_data = np.append(x_data, float(line.split()[0]))
#                 y_data = np.append(y_data, float(line.split()[1]))
#                 flux_error = np.append(flux_error, np.nan)
#
#             x_units = get_x_units(x_data)
#             y_units, y_factor = get_y_units(ctiodata)
#             # Strip off the 'f' for flux and extension
#             obj_name = spectra[1:].replace('.dat', '')
#         except StopIteration:
#             raise ImportError("Could not find ctio readme file")
#
#     elif spectra_file.endswith('.txt'):
#         data = open(spectra_file)  # read in data
#         # assuming 3 columns: wavelength, reflectance, error
#         x_data = np.array([])
#         y_data = np.array([])
#         flux_error = np.array([])
#         for line in data:
#             x_data = np.append(x_data, float(line.split()[0]))
#             y_data = np.append(y_data, float(line.split()[1]))
#             flux_error = np.append(flux_error, float(line.split()[2]))
#         x_units = get_x_units(x_data)
#         y_units, y_factor = get_y_units(y_data[0])
#         title = spectra.split('.')[0]
#         obj_name = title.lstrip('au').lstrip('0')  # assuming filename format from NEOx Characterization page
#
#     else:
#         raise ImportError("Invalid input file type. Input file must be '.fits', '.ascii', '.dat', or '.txt'")
#
#     # eliminate negative error values
#     with warnings.catch_warnings():
#         warnings.simplefilter("ignore")
#         y_data[np.logical_not(y_data > 0)] = np.nan
#         flux_error[np.logical_not(flux_error > 0)] = np.nan
#
#     wavelength = (x_data*x_units).to(u.AA)
#     # convert all wavelengths to Angstroms because it's easy to deal with that way
#     flux = y_data/y_factor*y_units
#     if not obj_name:
#         logger.warning("Could not parse object name from file")
#
#     #  Other --> [date_obs, tracking number, site code, Request Number]
#     return wavelength, flux, flux_error, x_units, y_units, obj_name, other
