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


class Command(BaseCommand):

    help = 'Convert ALCDEF into format DAMIT can use.'

    def add_arguments(self, parser):
        parser.add_argument('path', type=str, help='location of lightcurve data '
                                                   '(e.g. /apophis/eng/rocks/Reduction/aster123/)')

    def read_data(self):
        """ reads lightcurve_data.txt output by lightcurve_extraction"""
        f = open(options['lc_file'])
        lines = f.readlines()
        body = lines[0][8:-1]
        day1 = lines[1][5:10]
        times = np.array([])
        mags = np.array([])
        mag_errs = np.array([])
        for line in lines:
            try:
                chunks = line.split(' ')
                times = np.append(times, float(day1+chunks[0]))
                mags = np.append(mags, float(chunks[1]))
                mag_errs = np.append(mag_errs, float(chunks[2]))
            except ValueError:
                continue

        return times, mags, mag_errs, body

    def find_period(self, times, mags, mag_errs):
        """ Uses LombScargle routine to find period of light curve
            NOTE: currently not accurate nor finished yet
        """
        utimes = Time(times, format='mjd')
        ls = LombScargle(utimes.unix*u.s, mags*u.mag, mag_errs*u.mag)
        freq, power = ls.autopower()

        fig, ax = plt.subplots()
        ax.plot(freq, power)
        ax.set_xlabel('Frequencies Hz')
        ax.set_ylabel('L-S Power')

        fig2, ax2 = plt.subplots()
        ax2.plot(1/(freq*3600), power)
        ax2.set_xlabel('Period h')
        ax2.set_ylabel('L-S Power')

        period = (1/(freq[np.argmax(power)])).to(u.hour)
        self.stdout.write("Period: %.3f h" % period.value)
        return period.value

    def plot_fold_phase(self, phases, mags, mag_errs, period, epoch, title=''):
        """ plots phase-folded lightcurve given phases, magnitude, error, a period to fold over, and an epoch
            <phases>: list of phases or fraction each point in time is through a period from epoch.
            <mags>: magnitudes at each phase
            <mag_errs>: error in magnitudes at each phase
            <period>: period to fold against. (time at phase=1)-(time at phase=0)=period
            <epoch>: time to start first period at. Default is 0
            [title]: title of plot
        """
        fig, ax = plt.subplots()
        ax.errorbar(phases, mags, mag_errs, marker='.', linestyle=' ')
        ax.set_xlabel('phase')
        ax.set_ylabel('magnitude')
        ax.set_xlim(-.1, 1.1)
        ax.invert_yaxis()
        fig.suptitle(title)
        ax.set_title('(Period = %.3f h  Epoch = MJD%d)' % (period, epoch))
        plt.savefig('phased_lc.png')

        return

    def write_input_lcs(self):
        """
        Create input lcs:
        :input:
        :return:
        JD (Light-time corrected)
        Brightness (intensity)
        XYZ coordinates of Sun (astrocentric cartesian coordinates) AU
        XYZ coordinates of Earth (astrocentric cartesian coordinates) AU
        """

    def astro_centric_coord(self, geocent_a, heliocent_e):
        astrocent_e = [-1*x for x in geocent_a]
        geocent_h = [-1*x for x in heliocent_e]
        astrocent_h = [x_g - x_a for x_g, x_a in zip(geocent_h, geocent_a)]
        return astrocent_e, astrocent_h

    def handle(self, *args, **options):
        path = options['path']
        files = search(path, '.*.ALCDEF.txt')
        meta_list = []
        lc_list = []
        bodies = Body.objects.filter(name='4709')
        body = bodies[0]
        body_elements = model_to_dict(body)
        filt_name = "SG"
        for file in files:
            file = os.path.join(path, file)
            # basename = os.path.basename(file)
            meta_list, lc_list = import_alcdef(file, meta_list, lc_list)
        print(len([x for x in meta_list if x['FILTER'] in filt_name]))
        for k, dat in enumerate(meta_list):
            site = dat['MPCCODE']
            mean_intensity = 10 ** (0.4 * np.mean(lc_list[k]['mags']))
            if dat['FILTER'] in filt_name:
                print(f"{len(lc_list[k]['mags'])} 0")
                for c, d in enumerate(lc_list[k]['date']):
                    ephem_date = jd_utc2datetime(d)
                    ephem = compute_ephem(ephem_date, body_elements, site)
                    astrocent_e, astrocent_h = self.astro_centric_coord(ephem["geocnt_a_pos"], ephem["heliocnt_e_pos"])
                    d = d - ephem['ltt']/60/60/24
                    intensity = 10 ** (0.4 * lc_list[k]['mags'][c])
                    rel_intensity = intensity / mean_intensity
                    print(f"{d:.6f}   {rel_intensity:1.6E}   {astrocent_e[0]:.6E} {astrocent_e[1]:.6E} {astrocent_e[2]:.6E}"
                          f"   {astrocent_h[0]:.6E} {astrocent_h[1]:.6E} {astrocent_h[2]:.6E}")

        return
