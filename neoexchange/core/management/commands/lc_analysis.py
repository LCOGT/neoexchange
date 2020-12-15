"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2016-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

Prepare LC to be analysed with DAMIT
"""

import os
from glob import glob
from datetime import datetime, timedelta, time
from math import floor
import numpy as np

from django.core.management.base import BaseCommand, CommandError
from django.core.files.storage import default_storage

import matplotlib.pyplot as plt
from matplotlib.dates import HourLocator, DateFormatter
from astropy.stats import LombScargle
import astropy.units as u
from astropy.time import Time

from core.views import import_alcdef
from core.models import Body, model_to_dict
from core.utils import search
from astrometrics.time_subs import jd_utc2datetime
from astrometrics.ephem_subs import compute_ephem
from photometrics.catalog_subs import sanitize_object_name


class Command(BaseCommand):

    help = 'Convert ALCDEF into format DAMIT can use.'

    def add_arguments(self, parser):
        parser.add_argument('path', type=str, help='location of lightcurve data '
                                                   '(e.g. /apophis/eng/rocks/Reduction/aster123/)')
        parser.add_argument('-pmin', '--period_min', type=float, default=None, help='min period for period search (h)')
        parser.add_argument('-pmax', '--period_max', type=float, default=None, help='max period for period search (h)')
        parser.add_argument('-p', '--period', type=float, default=None, help='base period to search around (h)')

    # def read_data(self):
    #     """ reads lightcurve_data.txt output by lightcurve_extraction"""
    #     f = open(options['lc_file'])
    #     lines = f.readlines()
    #     body = lines[0][8:-1]
    #     day1 = lines[1][5:10]
    #     times = np.array([])
    #     mags = np.array([])
    #     mag_errs = np.array([])
    #     for line in lines:
    #         try:
    #             chunks = line.split(' ')
    #             times = np.append(times, float(day1+chunks[0]))
    #             mags = np.append(mags, float(chunks[1]))
    #             mag_errs = np.append(mag_errs, float(chunks[2]))
    #         except ValueError:
    #             continue
    #
    #     return times, mags, mag_errs, body
    #
    # def find_period(self, times, mags, mag_errs):
    #     """ Uses LombScargle routine to find period of light curve
    #         NOTE: currently not accurate nor finished yet
    #     """
    #     utimes = Time(times, format='mjd')
    #     ls = LombScargle(utimes.unix*u.s, mags*u.mag, mag_errs*u.mag)
    #     freq, power = ls.autopower()
    #
    #     fig, ax = plt.subplots()
    #     ax.plot(freq, power)
    #     ax.set_xlabel('Frequencies Hz')
    #     ax.set_ylabel('L-S Power')
    #
    #     fig2, ax2 = plt.subplots()
    #     ax2.plot(1/(freq*3600), power)
    #     ax2.set_xlabel('Period h')
    #     ax2.set_ylabel('L-S Power')
    #
    #     period = (1/(freq[np.argmax(power)])).to(u.hour)
    #     self.stdout.write("Period: %.3f h" % period.value)
    #     return period.value
    #
    # def plot_fold_phase(self, phases, mags, mag_errs, period, epoch, title=''):
    #     """ plots phase-folded lightcurve given phases, magnitude, error, a period to fold over, and an epoch
    #         <phases>: list of phases or fraction each point in time is through a period from epoch.
    #         <mags>: magnitudes at each phase
    #         <mag_errs>: error in magnitudes at each phase
    #         <period>: period to fold against. (time at phase=1)-(time at phase=0)=period
    #         <epoch>: time to start first period at. Default is 0
    #         [title]: title of plot
    #     """
    #     fig, ax = plt.subplots()
    #     ax.errorbar(phases, mags, mag_errs, marker='.', linestyle=' ')
    #     ax.set_xlabel('phase')
    #     ax.set_ylabel('magnitude')
    #     ax.set_xlim(-.1, 1.1)
    #     ax.invert_yaxis()
    #     fig.suptitle(title)
    #     ax.set_title('(Period = %.3f h  Epoch = MJD%d)' % (period, epoch))
    #     plt.savefig('phased_lc.png')
    #
    #     return

    def get_period_range(self, body, options):
        """
        Calculate period range to search from optional input parameters and known period
        :param body: Body object
        :param options: input options
        :return: pmin and pmax
        """
        pmin = options['period_min']
        pmax = options['period_max']
        period = options['period']
        if period is None or period <= 0:
            best_period = body.get_physical_parameters('P', False)
            if best_period:
                period = best_period[0].get('value', None)
            else:
                period = None
        if (pmin is None or pmin <= 0) and (pmax is None or pmax <= 0):
            if period is None:
                period = 1
            pmin = period - 0.5
            pmax = period + 0.5
        elif pmin and (pmax is None or pmax <= 0):
            pmax = pmin + 1
        elif pmin is None and pmax:
            pmin = pmax - 1
        if pmin <= 0:
            pmin = .5 * pmax
        return pmin, pmax

    def astro_centric_coord(self, geocent_a, heliocent_e):
        astrocent_e = [-1*x for x in geocent_a]
        geocent_h = [-1*x for x in heliocent_e]
        astrocent_h = [x_g - x_a for x_g, x_a in zip(geocent_h, geocent_a)]
        return astrocent_e, astrocent_h

    def create_lcs_input(self, input_file, meta_list, lc_list, body_elements, filt_name):
        """
        Create input lcs:
        :input:
        :return:
        JD (Light-time corrected)
        Brightness (intensity)
        XYZ coordinates of Sun (astrocentric cartesian coordinates) AU
        XYZ coordinates of Earth (astrocentric cartesian coordinates) AU
        """
        input_file.write(f"{len([x for x in meta_list if x['FILTER'] in filt_name])}\n")
        for k, dat in enumerate(meta_list):
            site = dat['MPCCODE']
            mean_intensity = 10 ** (0.4 * np.mean(lc_list[k]['mags']))
            if dat['FILTER'] in filt_name:
                input_file.write(f"{len(lc_list[k]['mags'])} 0\n")
                for c, d in enumerate(lc_list[k]['date']):
                    ephem_date = jd_utc2datetime(d)
                    ephem = compute_ephem(ephem_date, body_elements, site)
                    astrocent_e, astrocent_h = self.astro_centric_coord(ephem["geocnt_a_pos"], ephem["heliocnt_e_pos"])
                    d = d - ephem['ltt']/60/60/24
                    intensity = 10 ** (0.4 * lc_list[k]['mags'][c])
                    rel_intensity = intensity / mean_intensity
                    input_file.write(f"{d:.6f}   {rel_intensity:1.6E}   {astrocent_e[0]:.6E} {astrocent_e[1]:.6E}"
                                     f" {astrocent_e[2]:.6E}   {astrocent_h[0]:.6E} {astrocent_h[1]:.6E}"
                                     f" {astrocent_h[2]:.6E}\n")

    def import_or_create_psinput(self, path, obj_name, pmin, pmax):
        """
        If input_period_scan file exists, update period range, else create file from scratch
        :param path: path to working directory
        :param obj_name: sanitized object name
        :param pmin: minimum period
        :param pmax: maximum period
        :return: filename for input_period_scan
        """
        base_name = obj_name + '_input_period_scan'
        ps_input_filename = os.path.join(path, base_name)
        ps_input_file = default_storage.open(ps_input_filename, 'w+')
        lines = ps_input_file.readlines()
        if lines:
            lines[0] = f"{pmin} {pmax} 0.8	period start - end - interval coeff.\n"
            for line in lines:
                ps_input_file.write(line)
        else:
            ps_input_file.write(f"{pmin} {pmax} 0.8	period start - end - interval coeff.\n")
            ps_input_file.write(f"0.1			convexity weight\n")
            ps_input_file.write(f"6 6			degree and order of spherical harmonics\n")
            ps_input_file.write(f"8			no. of rows\n")
            ps_input_file.write(f"0.5	0		scattering parameters\n")
            ps_input_file.write(f"0.1	0\n")
            ps_input_file.write(f"-0.5	0\n")
            ps_input_file.write(f"0.1	0\n")
            ps_input_file.write(f"50	  		iteration stop condition\n")
            ps_input_file.write(f"10			minimum number of iterations (only if the above value < 1)\n")
        ps_input_file.close()
        return ps_input_filename

    def handle(self, *args, **options):
        path = options['path']
        files = search(path, '.*.ALCDEF.txt')
        meta_list = []
        lc_list = []
        for file in files:
            file = os.path.join(path, file)
            meta_list, lc_list = import_alcdef(file, meta_list, lc_list)
        names = list(set([x['OBJECTNUMBER'] for x in meta_list]))
        if len(names) != 1:
            self.stdout.write("Multiple objects Found.")
        bodies = Body.objects.filter(name=names[0])
        body = bodies[0]
        body_elements = model_to_dict(body)
        obj_name = sanitize_object_name(body.current_name())
        filt_name = "SG"
        lcs_input_filename = os.path.join(path, obj_name + '_input.lcs')
        lcs_input_file = default_storage.open(lcs_input_filename, 'w')
        self.create_lcs_input(lcs_input_file, meta_list, lc_list, body_elements, filt_name)
        lcs_input_file.close()
        pmin, pmax = self.get_period_range(body, options)
        psinput_filename = self.import_or_create_psinput(path, obj_name, pmin, pmax)

        return
