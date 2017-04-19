import os
from sys import exit
from datetime import datetime
from math import degrees, radians

from django.core.management.base import BaseCommand, CommandError
from django.forms.models import model_to_dict
import pyslalib.slalib as S
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
        parser.add_argument('-dm', '--deltamag', type=float, default=0.5, help='delta magnitude tolerance for multiple matches')
        parser.add_argument('--title', type=str, default=None, help='plot title')

    def plot_timeseries(self, times, mags, mag_errs, colors='r', title=''):
        fig, ax = plt.subplots()
        ax.plot(times, mags, color=colors, marker='.', linestyle=' ')
        ax.errorbar(times, mags, yerr=mag_errs, color=colors, linestyle=' ')
        ax.invert_yaxis()
        ax.set_xlabel('Time')
        ax.set_ylabel('Magnitude')
        ax.set_title(title)
        ax.minorticks_on()
        ax.xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))
        ax.fmt_xdata = DateFormatter('%H:%M:%S')
        fig.autofmt_xdate()
        plt.savefig("lightcurve.png")
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
        self.stdout.write("Searching within %.1f arcseconds and +/-%.1f delta magnitudes" % (options['boxwidth'], options['deltamag']))

        if len(frames) != 0:
            elements = model_to_dict(block.body)

            times = []
            mags = []
            mag_errs = []
            for frame in frames:
                emp_line = compute_ephem(frame.midpoint, elements, frame.sitecode)
                ra  = emp_line[1]
                dec = emp_line[2]
                mag_estimate = emp_line[3]
                (ra_string, dec_string) = radec2strings(ra, dec, ' ')
                sources = search_box(frame, ra, dec, options['boxwidth'])
                self.stdout.write("%s %s %s %s (%d) %s" % (frame.midpoint, ra_string, dec_string, frame.sitecode, len(sources), frame.filename))
                if len(sources) != 0:
                    if len(sources) == 1:
                        best_source = sources[0]
    #                    print "%.3f+/-%.3f" % (source.obs_mag, source.err_obs_mag)
                    elif len(sources) > 1:
                        min_sep = options['boxwidth'] * options['boxwidth']
                        for source in sources:
                            sep = S.sla_dsep(ra, dec, radians(source.obs_ra), radians(source.obs_dec))
                            sep = degrees(sep) * 3600.0
                            src_ra_string, src_dec_string = radec2strings(radians(source.obs_ra), radians(source.obs_dec))
                            delta_mag = abs(mag_estimate - source.obs_mag)
                            self.stdout.write("%s %s %s %s %.1f %.1f-%.1f %.1f" % ( ra_string, dec_string, src_ra_string, src_dec_string, sep, mag_estimate, source.obs_mag, delta_mag))
                            if sep < min_sep and delta_mag <= options['deltamag']:
                                min_sep = sep
                                best_source = source

                    times.append(frame.midpoint)
                    mags.append(best_source.obs_mag)
                    mag_errs.append(best_source.err_obs_mag)
  
            if options['title'] == None:
                plot_title = '%s from %s (%s) on %s' % (block.body.current_name(), block.site.upper(), frame.sitecode, block.when_observed.strftime("%Y-%m-%d"))
            else:
                plot_title = options['title']
            self.plot_timeseries(times, mags, mag_errs, title=plot_title)
