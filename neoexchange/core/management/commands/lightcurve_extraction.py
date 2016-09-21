import os
from sys import exit
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.forms.models import model_to_dict
import matplotlib.pyplot as plt
from matplotlib.dates import HourLocator, DateFormatter

from core.models import Block, Frame
from astrometrics.ephem_subs import compute_ephem, radec2strings
from photometrics.catalog_subs import search_box

class Command(BaseCommand):

    help = 'Extract lightcurves of a target from a given Block'

    def add_arguments(self, parser):
        parser.add_argument('blocknum', type=int, help='Block number to analyze')
        parser.add_argument('-bw', '--boxwidth', type=float, default=5.0, help='Boxwidth in arcsec to search')

    def plot_timeseries(self, times, mags, mag_errs, colors='r', title=''):
        fig, ax = plt.subplots()
        ax.plot(times, mags, color=colors, marker='.', linestyle=' ')
        ax.errorbar(times, mags, yerr=mag_errs, color=colors, linestyle=' ')
        ax.invert_yaxis()
        ax.set_xlabel('Time')
        ax.set_ylabel('Magnitude')
        ax.set_title(title)
        ax.xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))
        ax.fmt_xdata = DateFormatter('%H:%M:%S')
        fig.autofmt_xdate()
        plt.show()

        return

    def handle(self, *args, **options):

        self.stdout.write("==== Light curve building %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))

        try:
            block = Block.objects.get(id=options['blocknum'])
        except Block.DoesNotExist:
            self.stdout.write("Cannot find Block# %d" % options['blocknum'])
            exit(-1)
        
        self.stdout.write("Analyzing Block# %d for %s" % (block.id, block.body.current_name()))

        frames = Frame.objects.filter(block=block.id, zeropoint__isnull=False)
        self.stdout.write("Found %d frames for Block# %d with good ZPs" % (len(frames), block.id))
        self.stdout.write("Searching within %.1f arcseconds" % (options['boxwidth']))

        if len(frames) != 0:
            elements = model_to_dict(block.body)

            times = []
            mags = []
            mag_errs = []
            for frame in frames:
                emp_line = compute_ephem(frame.midpoint, elements, frame.sitecode)
                (ra_string, dec_string) = radec2strings(emp_line[1], emp_line[2], ' ')
                sources = search_box(frame, emp_line[1], emp_line[2], options['boxwidth'])
                self.stdout.write("%s %s %s %s (%d) %s" % (frame.midpoint, ra_string, dec_string, frame.sitecode, len(sources), frame.filename))
                if len(sources) == 1:
                    times.append(frame.midpoint)
                    source = sources[0]
                    mags.append(source.obs_mag)
                    mag_errs.append(source.err_obs_mag)
#                    print "%.3f+/-%.3f" % (source.obs_mag, source.err_obs_mag)
            plot_title = '%s from %s (%s) on %s' % (block.body.current_name(), block.site.upper(), frame.sitecode, block.when_observed.strftime("%Y-%m-%d"))
            self.plot_timeseries(times, mags, mag_errs, title=plot_title)
