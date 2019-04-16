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

Analyzes output of lightcurve_extraction for period and plots folded lightcurve
"""

import os
from datetime import datetime, timedelta, time
from math import floor
import numpy as np

from django.core.management.base import BaseCommand, CommandError

import matplotlib.pyplot as plt
from matplotlib.dates import HourLocator, DateFormatter
from astropy.stats import LombScargle
import astropy.units as u
from astropy.time import Time


class Command(BaseCommand):

    help = 'Takes in the output of \'lightcurve_extraction\' and analyses it for period while producing phase folded lightcurve plots. \'lightcure_extraction\' must have been run first.'

    def add_arguments(self, parser):
        parser.add_argument('lc_file', type=str, help='location of lightcurve data (e.g. /apophis/eng/rocks/Reduction/aster123/aster123_###_lightcurve_data.txt)')
        parser.add_argument('-p', '--period', type=float, default=0.0, help='Known Asteroid Rotation Period to fold plot against')
        parser.add_argument('-e', '--epoch', type=float, default=0.0, help='Epoch (MJD) to set initial phase with respect to')

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

    def handle(self, *args, **options):
        raise CommandError('This code requires more work before use.')

        try:
            times, mags, mag_errs, body = self.read_data()
        except FileNotFoundError:
            raise FileNotFoundError('{} not found. Please make sure you have included the correct directory and that lightcurve_extraction command has run'.format(options['lc_file']))
        if options['period'] == 0:
            period = self.find_period(times, mags, mag_errs)
        else:
            period = options['period']

        if not options['epoch']:
            epoch = times[np.argmin(times)]
        else:
            try:
                epoch = Time(options['epoch'], format='mjd').mjd
            except ValueError:
                raise ValueError('Epoch input in unrecognized format. Please input as MJD')

        subtime = times-epoch

        divtime = (subtime*24)/period
        phases = np.modf(divtime)[0]  # phases array built

        data = sorted(zip(phases, mags, mag_errs))  # building buffers
        end = np.array([])
        start = np.array([])
        for n in range(len(data)):
            if data[n][0] >= .90:
                start = np.append(start, [data[n][0]-1, data[n][1], data[n][2]])
            if data[n][0] <= .1:
                end = np.append(end, [data[n][0]+1, data[n][1], data[n][2]])
        data = np.append(data, end)
        data = np.append(start, data)
        phases = data[::3]
        mags = data[1::3]
        mag_errs = data[2::3]

        phasetitle = 'Phase Folded LC for %s' % body

        self.plot_fold_phase(phases, mags, mag_errs, period, epoch, phasetitle)
        plt.show()

        return
