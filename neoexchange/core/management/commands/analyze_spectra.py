"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2017-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.files.storage import default_storage
from astropy.io import fits
from astropy.wcs import WCS
from astropy import units as u
import urllib
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import csv
import argparse
import re
import os
import logging

logger = logging.getLogger(__name__)


def read_mean_tax():
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


def stand_plot(ax, stand_tax):
    spec_dict = read_mean_tax()
    lam = np.array(spec_dict['Wavelength'])
    lam *= 10000
    for tax in stand_tax:
        tax = tax.lower().capitalize()
        tax_mean = tax+'_Mean'
        tax_sig = tax+'_Sigma'
        try:
            yyy = np.array(spec_dict[tax_mean])
            yyy_error = np.array(spec_dict[tax_sig])
        except KeyError:
            print("No such taxonomy as {}.".format(tax))
            continue
        y_err_upper = yyy + yyy_error
        y_err_lower = yyy - yyy_error

        test = [j for j, x in enumerate(lam) if 3500 < x < 10500]

        color = next(ax._get_lines.prop_cycler)['color']
        ax.plot(lam[test], y_err_upper[test], linestyle=":", color=color, alpha=.5)
        ax.plot(lam[test], y_err_lower[test], linestyle=":", color=color, alpha=.5)
        ax.plot(lam[test], yyy[test], color=color, label=tax_mean, alpha=.5)


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

    s = np.r_[x[window_len-1:0:-1], x, x[-2:-window_len-1:-1]]
    # print(len(s))
    if window == 'flat':  # moving average
        w = np.ones(window_len, 'd')
    else:
        w = eval('np.'+window+'(window_len)')

    y = np.convolve(w/w.sum(), s, mode='valid')

    return y[(window_len // 2 - 1):-(window_len // 2)]


def pull_data_from_spectrum(spectra):
    file = default_storage.open(spectra)
    try:
        hdul = fits.open(file)
    except FileNotFoundError:
        print("Cannot find file {}".format(file))
        return None, None, None

    data = hdul[0].data
    hdr = hdul[0].header

    yyy = data[0][0]
    w = WCS(hdr, naxis=1, relax=False, fix=False)
    lam = w.wcs_pix2world(np.arange(len(yyy)), 0)[0]

    wavelength = get_x_units(lam)
    flux = get_y_units(yyy, spectra)
    return wavelength, flux, hdr


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


def get_y_units(y_data, filename):
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

    elif '_2df_ex.fits' in filename:  # from FLOYDS
        y_factor = 10**20
        y_units = u.erg/(u.cm**2)/u.s/u.AA

    else:
        logger.warning("Could not parse flux units from file. Assuming erg/cm^2/s/A")
        y_units = u.erg/(u.cm**2)/u.s/u.AA

    yyy = np.array(y_data)
    flux = ((yyy / y_factor) * y_units)
    return flux


def pull_data_from_text(spectra):
    if default_storage.exists(spectra):
        with default_storage.open(spectra, mode='rb') as f:
            lines = f.read()
    else:
        try:
            with urllib.request.urlopen(spectra) as f:
                lines = f.read()
        except ValueError:
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
    flux = get_y_units(yyy, spectra)
    return wavelength, flux, err


def spectrum_plot(spectra, data_set='', analog=None, offset=0):
    windows = ['flat', 'hanning', 'hamming', 'bartlett', 'blackman']
    spec_x, spec_y, spec_header = pull_data_from_spectrum(spectra)
    if spec_y is None:
        return data_set, None, None

    box = 100

    if analog:
        analog_x, analog_y, analog_header = pull_data_from_spectrum(analog)
        if analog_y is None:
            yyy = spec_y
            analog = None
        else:
            spec_y_sm = smooth(spec_y, box, windows[1])
            analog_y_sm = smooth(analog_y, box, windows[1])
            if len(spec_y_sm) >= len(analog_y_sm):
                yyy = spec_y_sm[:len(analog_y_sm)] / analog_y_sm
            else:
                yyy = spec_y_sm / analog_y_sm[:len(spec_y_sm)]
    else:
        yyy = spec_y

    if not data_set:
        if analog:
            data_set = "{} -- {} -- {}".format(spec_header['OBJECT'], analog_header['OBJECT'], spec_header['DAY-OBS'])
        else:
            data_set = "{} -- {}".format(spec_header['OBJECT'], spec_header['DAY-OBS'])
    elif data_set.upper() == 'NONE':
        data_set = ''

    xxx = spec_x[:len(yyy)]

    smoothy = yyy

    upper_wav = 10000*u.AA
    if analog:
        lower_wave = 4000*u.AA
    else:
        lower_wave = 3100*u.AA

    y_clipped = np.take(smoothy, np.argwhere((lower_wave < xxx) & (xxx < upper_wav)).flatten())
    x_clipped = np.take(xxx, np.argwhere((lower_wave < xxx) & (xxx < upper_wav)).flatten())

    find_g = np.take(smoothy, np.argwhere((5400*u.AA < xxx) & (xxx < 5600*u.AA)).flatten())
    y_clipped /= np.mean(find_g)
    y_clipped += 0.2*offset

    return data_set, y_clipped, x_clipped


class Command(BaseCommand):
    help = 'This code converts a fits file trace into a normalized reflectance spectrum using a solar analog.'

    def add_arguments(self, parser):
        parser.add_argument("--outpath", help="Output path for plots", type=str, default='./')
        parser.add_argument("--path", help="base path spectra", type=str, default='~')
        parser.add_argument("--title", help="Title for Plot", type=str, default='Normalized Spectra')

    def handle(self, *args, **options):
        path = options['path']
        outpath = options['outpath']
        title = options['title']
        trace = 'test'
        reflec = True
        if path[-1] != '/':
            path += '/'
        if outpath[-1] != '/':
            outpath += '/'

        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1, title=title)

        print("List the taxonomic standards to plot. (comma separated format. => X, C, B) ")
        print("Possible standards include: A,B,C,Cb,Cg,Cgh,Ch,D,K,L,O,Q,R,S,Sa,Sq,Sr,Sv,T,V,X,Xc,Xe,Xk,Xn,None")
        stand_tax = input("Taxonomic Standards:")

        if stand_tax and 'NONE' not in stand_tax.upper():
            stand_tax = list(filter(None, re.split(r',|\s|;|\.|/|-', stand_tax)))
            stand_plot(ax, stand_tax)

        while trace:
            print("=========================================================================")
            print("Input the path to the 1D merged asteroid trace (Leave blank to skip).")
            print("If using the FLOYDS pipeline, this will be of the form 'trim_ntt*_merge_*_e.fits or ntt*_merge_*2df_ex.fits")
            trace = input("Path to asteroid trace:")

            if trace:
                print("=========================================================================")
                print("Input the path to the 1D merged solar analog trace to be removed from this spectrum (Leave blank to skip).")
                print("If using the FLOYDS pipeline, this will be of the form 'trim_ntt*_merge_*_e.fits or ntt*_merge_*2df_ex.fits")
                sol_trace = input("Path to solar analog trace:")
                if not sol_trace:
                    reflec = False
                    sol_path_trace = ''
                else:
                    sol_path_trace = path + sol_trace

                print("=========================================================================")
                print("Input label for these data (Leave blank for default, for no label type 'None').")
                print("Default = {object} -- {analog} -- {obj date}")
                label = input("Data label:")

                print(path+trace)
                data_set, normalized_ast_spec, ast_wav = spectrum_plot(path + trace, label, sol_path_trace)
                ax.plot(ast_wav, normalized_ast_spec, label=data_set)

            if reflec:
                ax.set_ylabel('Reflectance Spectra (Normalized at $5500 \AA$)')
            else:
                ax.set_ylabel('Relative Spectra (Normalized at $5500 \AA$)')
            ax.set_xlabel('Wavelength ($\AA$)')
            ax.legend()
            plt.savefig(outpath + 'temp.png')
            print('New spectroscopy plot saved to {}'.format(outpath + 'temp.png'))
