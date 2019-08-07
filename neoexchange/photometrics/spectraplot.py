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
from astropy.convolution import convolve, Box1DKernel  # Gaussian1DKernel
from astropy.wcs import WCS
from astropy import units as u
from datetime import datetime
import matplotlib.pyplot as plt
import os
import io
from glob import glob
import logging
import numpy as np
import collections
import warnings
import re

from django.core.files.storage import default_storage

from photometrics.external_codes import unpack_tarball

logger = logging.getLogger(__name__)


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
                rn = hdr['REQNUM'].lstrip('0')
            except KeyError:
                tn = site = inst = None
            try:
                date_obs = hdr['DATE-OBS']
            except KeyError:
                date_obs = hdr['DATE_OBS']
            date = datetime.strptime(date_obs, '%Y-%m-%dT%H:%M:%S.%f')
            other = [date, tn, site, rn]
            x_units = get_x_units(x_data)
            y_units, y_factor = get_y_units(hdr)
            check_norm(hdul[0].header.values())  # check if data is already normalized

    elif spectra_file.endswith('.ascii'):
        data = ascii.read(spectra_file)  # read in data
        # assuming 3 columns: wavelength, flux/reflectance, error
        columns = data.keys()
        x_data = data[columns[0]]  # converting tables to ndarrays
        y_data = data[columns[1]]
        flux_error = data[columns[2]]
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
            # Strip off the 'f' for flux and extension
            obj_name = spectra[1:].replace('.dat', '')
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
    flux = y_data/y_factor*y_units
    if not obj_name:
        logger.warning("Could not parse object name from file")

    #  Other --> [date_obs, tracking number, site code, Request Number]
    return wavelength, flux, flux_error, x_units, y_units, obj_name, other


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
        try:
            stds = np.append(stds, np.nanstd(normy[loc-noise_window:loc]).value)
        except AttributeError:
            stds = np.append(stds, np.nanstd(normy[loc-noise_window:loc]))
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


def normalize(x, y, wavelength=5500*u.AA, width=500*u.AA):
    """normalizes flux data with a specific wavelength flux value
       inputs: <x>: wavelenth data (Quantity type)
               <y>: flux data (Quantity type)
               [wavelength]: target wavelength to normalize at (Quantity type)
               [width]: width of region overwhich to draw the normalization value
       outputs: normalized flux data
    """
    n_high = np.abs(x-wavelength-width/2).argmin()
    n_low = np.abs(x-wavelength+width/2).argmin()
    normval = np.nanmean(y[n_low:n_high])

    return y/normval  # REMEMBER to normalize y-units too if normalizing final data


def update_label(old_label, exponent_text):
    if exponent_text == "":
        return old_label

    try:
        units = old_label[old_label.index("[") + 1:old_label.rindex("]")]
    except ValueError:
        units = ""
    label = old_label.replace("[{}]".format(units), "")

    exponent_text = exponent_text.replace("\\times", "")

    return "{} [{} {}]".format(label, exponent_text, units)


def format_label_string_with_exponent(ax, axis='both'):
    """ Format the label string with the exponent from the ScalarFormatter
    http://greg-ashton.physics.monash.edu/setting-nice-axes-labels-in-matplotlib.html
    """
    ax.ticklabel_format(axis=axis, style='sci')

    axes_instances = []
    if axis in ['x', 'both']:
        axes_instances.append(ax.xaxis)
    if axis in ['y', 'both']:
        axes_instances.append(ax.yaxis)

    for ax in axes_instances:
        ax.major.formatter._useMathText = True
        plt.draw()  # Update the text
        exponent_text = ax.get_offset_text().get_text()
        label = ax.get_label().get_text()
        ax.offsetText.set_visible(False)
        ax.set_label_text(update_label(label, exponent_text))


def plot_spectra(x, y, y_units, x_units, ax, title, ref=0, norm=0, log=False):
    """plots spectra data
       imputs: <x>: wavelength data for x axis
               <y>: flux data for y axis
               <ax>: matplotlib axis
               <title>: plot title (should be object name)
               [ref]: 1 for sol_ref, 0 for asteroid
               [norm]: normalizes data when set to 1
               [log]: if the y data is a logarithmic quantity when True
    """

    if norm == 1:
        yyy = normalize(x, y)
    else:
        yyy = y

    ax.plot(x, yyy, linewidth=1)
    ax.set_xlabel('Wavelength ({})'.format(x_units.to_string('latex_inline')))
    y_units_label = y_units.to_string('latex_inline')
    if log:
        y_units_label = '$\\log_{10} \\mathrm{F}_\\lambda\\ (' + y_units_label[1:] + ')'
    ax.set_ylabel(y_units_label)
    format_label_string_with_exponent(ax, axis='y')
    ax.minorticks_on()

    if title:
        ax.set_title(title)
    else:
        if ref:
            ax.set_title("Solar Analog")
        else:
            ax.set_title("Asteroid")

    # set axis values
    peak_idx = np.searchsorted(x, 5000*u.AA)
    try:
        ax.set_xlim(x[0].value, x[-1].value)
        if log is False:
            ax.set_ylim(0, (yyy[peak_idx]*2))
    except ValueError:
        pass
    except u.UnitsError:
        pass


def get_spec_plot(path, spectra, obs_num, basepath="", log=False):

    if not os.path.exists(os.path.join(path, spectra)):
        logger.error("Could not open: " + os.path.join(path, spectra))
        return None

    fig, ax = plt.subplots()
    x, y, yerr, xunits, yunits, name, details = read_spectra(path, spectra)
    if not name:
        name = "????"
    if details:
        title = 'UTC Date: {}'.format(details[0].strftime('%Y/%m/%d %X'))
        fig.suptitle('Request Number {} -- {} at {}'.format(details[3], name, details[2]))
        obs_details = "_" + details[3]
    else:
        title = name.upper().replace('_', '-')
        obs_details = ''
    if log:
        # Adjust left side of subplot to give a little more room
        fig.subplots_adjust(left=0.175)
        y_log = np.log10(y.value)
        xsmooth, ysmooth = smooth(x, y_log)
    else:
        xsmooth, ysmooth = smooth(x, y)
    plot_spectra(xsmooth, ysmooth, yunits, xunits, ax, title, log=log)

    path = path.replace(basepath,"").lstrip("/")
    plot_filename = os.path.join(path, name.replace(' ', '_') + obs_details + "_spectra_" + str(obs_num) + ".png")

    save_file = default_storage.open(plot_filename,"w")
    fig.savefig(save_file, format='png')
    plt.close()
    save_file.close()

    # Write raw data to ascii file
    save_file = default_storage.open(plot_filename.replace('.png', '.ascii'), "w")
    ascii.write([x, y, yerr], save_file, names=['Wavelength ({})'.format(xunits), 'Flux ({})'.format(yunits), 'Flux_error'], overwrite=True)
    save_file.close()

    return save_file

def make_spec(date_obs, obj, req, indir, basepath, prop, obs_num):
    """Creates plot of spectra data for spectra blocks
       <pk>: pk of block (not superblock)
    """
    path = os.path.join(indir, obj + '_' + req)
    filenames = glob(os.path.join(path, '*_2df_ex.fits'))  # checks for file in path
    # filenames = [os.path.join(path,f) for f in default_storage.listdir(path)[1] if f.endswith("*_2df_ex.fits")]
    spectra_path = None
    tar_path = unpack_path = None
    obs_num = str(obs_num)
    if filenames:
        spectra_path = filenames[int(obs_num)-1]
        spec_count = len(filenames)
    else:
        tar_files = glob(os.path.join(indir, prop+'_*'+req+'*.tar.gz'))  # if file not found, looks for tarball
        if tar_files:
            for tar in tar_files:
                if req in tar:
                    tar_path = tar
                    unpack_path = os.path.join(indir, obj+'_'+req)
            if not tar_path and not unpack_path:
                logger.error("Could not find tarball for request: %s" % req)
                return None, None
            spec_files = unpack_tarball(tar_path, unpack_path)  # upacks tarball
            spec_list = [spec for spec in spec_files if '_2df_ex.fits' in spec]
            spectra_path = spec_list[int(obs_num)-1]
            spec_count = len(spec_list)
        else:
            logger.error("Could not find spectrum data or tarball for request: %s" % req)
            return None, None

    if spectra_path:  # plots spectra
        spec_file = os.path.basename(spectra_path)
        spec_dir = os.path.dirname(spectra_path)
        spec_plot = get_spec_plot(spec_dir, spec_file, obs_num, basepath=basepath)
        return spec_plot, spec_count

    else:
        logger.error("Could not find spectrum data for request: %s" % req)
        return None, None
