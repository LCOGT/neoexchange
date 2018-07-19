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

    def add_arguments(self, parser):
        parser.add_argument('-p', '--period', type=float, default=0.0, help='Known Asteroid Rotation Period to fold plot against')

    def read_data(self,path):

        f = open(path)
        lines = f.readlines()
        body = lines[0][8:-1]
        day1 = lines[1][5:10]
        daylast = floor(float(day1 + lines[-1][:6]))
        times = np.array([])
        mags = np.array([])
        mag_errs = np.array([])
        for line in lines:
            try:
                times = np.append(times,float(day1+line[1:7]))
                mags = np.append(mags,float(line[8:13]))
                mag_errs = np.append(mag_errs,float(line[15:20]))
            except ValueError:
                continue

        return times, mags, mag_errs, body

    def find_period(self, times, mags, mag_errs):

        utimes = Time(times,format='mjd')
        ls = LombScargle(utimes.unix*u.s,mags*u.mag,mag_errs*u.mag)
        freq, power = ls.autopower()

        fig, ax = plt.subplots()
        ax.plot(freq,power)
        ax.set_xlabel('Frequencies Hz')
        ax.set_ylabel('L-S Power')

        fig2, ax2 = plt.subplots()
        ax2.plot(1/(freq*3600),power)
        ax2.set_xlabel('Period h')
        ax2.set_ylabel('L-S Power')

        period = (1/(freq[np.argmax(power)])).to(u.hour)
        self.stdout.write("Period: %.3f h" % period.value)
        return period.value

    def plot_fold_phase(self,phases,mags,mag_errs,period,title):

        fig, ax = plt.subplots()
        ax.errorbar(phases,mags,mag_errs, marker='.', linestyle=' ')
        ax.set_xlabel('phase')
        ax.set_ylabel('magnitude')
        ax.set_xlim(0,1)
        ax.invert_yaxis()
        fig.suptitle(title)
        ax.set_title('(Period = %.3f h)' % period)
        plt.savefig('phased_lc.png')


        return

    def handle(self, *args, **options):

        try:
            times, mags, mag_errs, body = self.read_data('lightcurve_data.txt')
        except FileNotFoundError:
            raise FileNotFoundError('\"lightcurve_data.txt\" not found. Please make sure you are in the correct directory and the \"lightcurve_extraction\" command has run')
        if options['period'] == 0:
            period = self.find_period(times, mags,mag_errs)
        else:
            period = options['period']

        subtime = (times-times[np.argmin(times)])
        divtime = (subtime*24)/period
        phases = np.modf(divtime)[0]

        #data = sorted(zip(phases,mags))

    #    for n in range(len(data)):
        #    if data[n][0] >= .95
        #        data = data

        phasetitle = 'Phase Folded LC for %s' % body

        self.plot_fold_phase(phases,mags,mag_errs,period,phasetitle)
        plt.show()

        return
