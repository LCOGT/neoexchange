"""
convert 1D fits spectra into a readable plot
Author: Adam Tedeschi
Date: 6/25/2018
for NeoExchange
"""

from astropy.io import fits, ascii
from astropy.convolution import convolve, Box1DKernel  # Gaussian1DKernel
from astropy.wcs import WCS
from astropy import units as u
import matplotlib.pyplot as plt
import os
import io
from glob import glob
import logging
# import matplotlib.ticker as ticker
import numpy as np
import collections
import warnings
import re

logger = logging.getLogger(__name__)

# np.set_#printoptions(threshold=np.inf)


def check_norm(values):  # not perfect
    """checks with fits standard parsing and notifies if flux data has been normalized already
       input: <values>: array of text values in .fits header to parse
    """
    for value in values:
        if "NORMALIZED TO" in str(value).upper():
            normstr = value
            for s in normstr.split():
                try:
                    normval = float(s)
                    normloc = list(float(t) for t in re.findall(r'-?\d+\.?\d*', normstr))[-1]
                    logger.info("Flux normalized to {} at {}".format(normval, normloc))
                except ValueError:
                    continue


def get_x_units(x_data):
    """finds wavelength units from x_data
       inputs: <xdata>: unitless wavelength data
       outputs: x_units
    """
    x_min = np.amin(x_data)

    # assuming visible to NIR range (~3000-10000A)
    if x_min > 1000:
        x_units = u.AA  # (Angstroms)
    elif 100 < x_min < 800:
        x_units = u.nm
    elif .1 < x_min < 1:
        x_units = u.micron
    else:
        logger.warning("Could not parse wavelength units from file. Assuming Angstoms")
        x_units = u.AA

    return x_units


def get_y_units(info):
    """finds flux/reflectance units
       inputs: <info>: .fits header, .ascii metadata, point from .txt file, or ESO spec standard readme
       outputs: y_units,factor
    """
    y_factor = 1
    y_units = None
    flux_id = ["ERG", "FLAM"]  # IDs to look for units with
    # I know erg isn't the full unit, but it's a good indicator.
    norm_id = ["NORM", "UNITLESS", "NONE"]  # IDs to look for normalizations with
    refl_id = ["REFLECT"]  # IDs to look for normalized reflectance

    if isinstance(info, list):  # from ESO aaareadme.ctio
        for line in info:
            if 'ergs' in line:
                normlocs = list(float(t) for t in re.findall(r'-?\d+\.?\d*', line))
                y_units = u.erg/(u.cm**2)/u.s/u.AA
                try:
                    y_factor = normlocs[-2]**normlocs[-1]
                except IndexError:
                    pass
                break

    elif isinstance(info, float):  # from .txt file (assuming normalized reflectance)
        y_units = u.def_unit("Normalized_Reflectance", u.dimensionless_unscaled)

    elif isinstance(info, collections.OrderedDict):  # from .ascii
        head = np.array(info.values())
        col_head = ''.join(map(str, head.flatten()))
        if any(unit_id in col_head.upper() for unit_id in flux_id):  # checking for flam
            y_units = u.erg/(u.cm**2)/u.s/u.AA
        elif any(unit_id in col_head.upper() for unit_id in norm_id):  # checking for normalized
            if any(unit_id2 in col_head.upper() for unit_id2 in refl_id):  # checking for normalization
                y_units = u.def_unit("Normalized_Reflectance", u.dimensionless_unscaled)
                logger.info("Spectra y_units: {}".format(y_units))
            else:
                y_units = u.def_unit("Normalized_Flux", u.dimensionless_unscaled)
                logger.info("Spectra y_units: normalized")
        elif any(unit_id in col_head.upper() for unit_id in refl_id):  # checking for normalized reflectance
            y_units = u.def_unit("Normalized_Reflectance", u.dimensionless_unscaled)
            logger.info("Spectra y_units: {}".format(y_units))
        else:
            pass

    elif isinstance(info, fits.header.Header):  # from .fits
        possible_keys = ['BUNIT', 'TUNIT2']  # can add more  if needed
        keys = list(info.keys())
        for n in range(len(keys)):
            if any(key_id in keys[n] for key_id in possible_keys):
                if any(unit_id in info[keys[n]].upper() for unit_id in flux_id):
                    if "10^20" in info[keys[n]]:  # special LCO standard case
                        y_factor = 10**20
                    y_units = u.erg/(u.cm**2)/u.s/u.AA
                elif any(unit_id in info[keys[n]].upper() for unit_id in norm_id):
                    if any(unit_id in info[keys[n]].upper() for unit_id in refl_id):  # checking for normalization
                        y_units = u.def_unit("Normalized_Reflectance", u.dimensionless_unscaled)
                        logger.info("Spectra y_units: {}".format(y_units))
                    else:
                        y_units = u.def_unit("Normalized_Flux", u.dimensionless_unscaled)
                        logger.info("Spectra y_units: normalized")
                elif any(unit_id in info[keys[n]].upper() for unit_id in refl_id):  # checking for normalized reflectance
                    y_units = u.def_unit("Normalized_Reflectance", u.dimensionless_unscaled)
                    logger.info("Spectra y_units: {}".format(y_units))
                else:
                    pass

    if y_units is None:
        logger.warning("Could not parse flux units from file. Assuming erg/cm^2/s/A")
        y_units = u.erg/(u.cm**2)/u.s/u.AA

    return y_units, y_factor


def read_spectra(path, spectra):
    """reads in all important data from spectra file (Works for .ascii 2 .fits standards, and .txt)
       inputs: <spectra_file>: path and file name to spectra
       outputs: wavelength (Quantity type), flux, flux_error, x_units, y_units, obj_name
    """
    spectra_file = os.path.join(path, spectra)
    other = None
    if spectra_file.endswith('.fits'):
        with fits.open(spectra_file, ignore_missing_end=True) as hdul:  # read in data
            # LCO fits standard:
            if hdul[0].data is not None:
                data = hdul[0].data
                hdr = hdul[0].header
                y_data = data.flatten()[:max(data.shape)]
                w = WCS(hdr, naxis=1, relax=False, fix=False)

                x_data = w.wcs_pix2world(np.arange(len(y_data)), 0)[0]

                try:
                    flux_error = np.array(data[3][0])
                except IndexError:
                    logger.warning("Could not parse error data for spectra")
                    flux_error = np.zeros(len(x_data))
            # fits standard 2:
            elif hdul[1].data is not None:
                data = hdul[1].data
                hdr = hdul[1].header
                x_data = np.array(list(n[0] for n in data))
                y_data = np.array(list(n[1] for n in data))

                if len(data[0]) > 2:
                    flux_error = np.array(list(n[2] for n in data))
                else:
                    flux_error = np.zeros(len(x_data))
            else:
                raise ImportError("Could not read data from .fits file")

            try:
                obj_name = hdr['OBJECT']
            except KeyError:
                obj_name = ''
            try:
                tn = hdr['TRACKNUM'].lstrip('0')
                site = hdr['SITEID'].upper()
            except KeyError:
                tn = site = inst = None
            try:
                date_obs = hdr['DATE-OBS']
            except KeyError:
                date_obs = hdr['DATE_OBS']

            other = [date_obs, tn, site]
            x_units = get_x_units(x_data)
            y_units, y_factor = get_y_units(hdr)
            check_norm(hdul[0].header.values())  # check if data is already normalized

    elif spectra_file.endswith('.ascii'):
        data = ascii.read(spectra_file)  # read in data
        # assuming 3 columns: wavelength, flux/reflectance, error
        x_data = data['col1']  # converting tables to ndarrays
        y_data = data['col2']
        flux_error = data['col3']
        x_units = get_x_units(x_data)
        y_units, y_factor = get_y_units(data.meta)
        obj_name = ""  # No way to read object name from ascii files right now.

    elif spectra_file.endswith('.dat'):  # assuming origin is ESO spec standards
        data = open(spectra_file)  # read in data
        filename = glob(os.path.join(path, '*readme.ctio'))
        if filename:
            ctio = filename[0]
            ctiodata = open(ctio)
            x_data = np.array([])
            y_data = np.array([])
            flux_error = np.array([])
            for line in data:
                x_data = np.append(x_data, float(line.split()[0]))
                y_data = np.append(y_data, float(line.split()[1]))
                flux_error = np.append(flux_error, np.nan)

            x_units = get_x_units(x_data)
            y_units, y_factor = get_y_units(list(ctiodata.readlines()))
            obj_name = spectra.lstrip('f').replace('.dat', '')
        else:
            raise ImportError("Could not find ctio readme file")

    elif spectra_file.endswith('.txt'):
        data = open(spectra_file)  # read in data
        # assuming 3 columns: wavelength, reflectance, error
        x_data = np.array([])
        y_data = np.array([])
        flux_error = np.array([])
        for line in data:
            x_data = np.append(x_data, float(line.split()[0]))
            y_data = np.append(y_data, float(line.split()[1]))
            flux_error = np.append(flux_error, float(line.split()[2]))
        x_units = get_x_units(x_data)
        y_units, y_factor = get_y_units(y_data[0])
        title = spectra.split('.')[0]
        obj_name = title.lstrip('au').lstrip('0')  # assuming filename format from NEOx Characterization page

    else:
        raise ImportError("Invalid input file type. Input file must be '.fits', '.ascii', '.dat', or '.txt'")

    # eliminate negative error values
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        y_data[np.logical_not(y_data > 0)] = np.nan
        flux_error[np.logical_not(flux_error > 0)] = np.nan

    wavelength = (x_data*x_units).to(u.AA)
    # convert all wavelengths to Angstroms because it's easy to deal with that way
    flux = y_data*y_units

    if not obj_name:
        logger.warning("Could not parse object name from file")

    return wavelength, flux, flux_error, x_units, y_units, y_factor, obj_name, other


def smooth(x, y):
    """uses boxcar averaging to smooth flux data if necessary
       inputs: <ydata>: raw flux data
       outputs: smoothed flux data
    """

    # determining if smoothing is needed and to what degree
    stds = np.array([])
    normy = normalize(x, y)
    noise_window = 5
    loc = noise_window
    window_num = 8

    while loc <= len(x):
        stds = np.append(stds, np.nanstd(normy[loc-noise_window:loc]).value)
        loc += int(len(x)/window_num)

    noisiness = np.nanmean(stds/((x[-1]-x[0])/len(x)).value)
    # determines 'noisiness' by looking at the std. dev. of chunks of points of size
    # 'noise_window' at 'window_num' spots in the data

    if .0035 <= noisiness < .005:
        window = 15
        logger.info("smoothing: yes (15)")
    elif .005 <= noisiness < .01:
        window = 20
        logger.info("smoothing: yes (20)")
    elif noisiness >= .01:
        window = 30
        logger.info("smoothing: yes(30)")
    else:
        logger.info("smoothing: no")
        return x, y

    # smoothing
    return x[int(window/2):-int(window/2)], convolve(y, Box1DKernel(window))[int(window/2):-int(window/2)]  # boxcar average data


def normalize(x, y, wavelength=5500*u.AA):
    """normalizes flux data with a specific wavelength flux value
       inputs: <x>: wavelenth data (Quantity type)
               <y>: flux data (Quantity type)
               [wavelength]: target wavelength to normalize at (Quantity type)
       outputs: normalized flux data
    """
    n = np.abs(x-wavelength).argmin()
    normval = y[n]
    while (not normval.value or np.isnan(normval.value)) and n < len(x)-2:
        normval = y[n]  # uses closest data point to target wavelength
        n += 1
    if not normval.value or np.isnan(normval.value):
        normval = 1

    return y/normval  # REMEMBER to normalize y-units too if normalizing final data


def plot_spectra(x, y, y_units, ax, title, ref=0, norm=0,):
    """plots spectra data
       imputs: <x>: wavelength data for x axis
               <y>: flux data for y axis
               <ax>: matplotlib axis
               <title>: plot title (should be object name)
               [ref]: 1 for sol_ref, 0 for asteroid
               [norm]: normalizes data when set to 1
    """

    if norm == 1:
        yyy = normalize(x, y)
    else:
        yyy = y

    ax.plot(x, yyy, linewidth=1)
    ax.set_xlabel(r"Wavelength ($\AA$)")
    ax.set_ylabel(y_units.to_string('latex_inline'))
    ax.minorticks_on()
    ax.tick_params(axis='y', which='minor', left=False)
    if title:
        ax.set_title(title)
    else:
        if ref:
            ax.set_title("Solar Analog")
        else:
            ax.set_title("Asteroid")

    # set axis values
    peak_idx = np.searchsorted(x, 5000*u.AA)
    ax.axis([x[0].value, x[-1].value, 0, (y[peak_idx]*2)])


def get_spec_plot(path, spectra):

    fig, ax = plt.subplots()
    x, y, yerr, xunits, yunits, yfactor, name, details = read_spectra(path, spectra)
    if not name:
        name = "????"
    if details:
        title = 'UT Date: {}'.format(details[0])
        fig.suptitle('Tracking Number {} -- {} at {}'.format(details[1], name, details[2]))
    else:
        title = name
    xsmooth, ysmooth = smooth(x, y)
    plot_spectra(xsmooth, ysmooth/yfactor, yunits, ax, title)
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    plt.close()

    return fig, buffer
