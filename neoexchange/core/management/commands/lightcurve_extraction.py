import os
from sys import exit
from datetime import datetime
from math import degrees, radians

from django.core.management.base import BaseCommand, CommandError
from django.forms.models import model_to_dict
try:
    import pyslalib.slalib as S
except:
    pass
import matplotlib.pyplot as plt
from matplotlib.dates import HourLocator, DateFormatter

from core.models import Block, Frame, SourceMeasurement
from astrometrics.ephem_subs import compute_ephem, radec2strings
from astrometrics.time_subs import datetime2mjd_utc
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

    def make_source_measurement(self, body, frame, cat_source, persist=False):
        source_params = { 'body' : body,
                          'frame' : frame,
                          'obs_ra' : cat_source.obs_ra,
                          'obs_dec' : cat_source.obs_dec,
                          'obs_mag' : cat_source.obs_mag,
                          'err_obs_ra' : cat_source.err_obs_ra,
                          'err_obs_dec' : cat_source.err_obs_dec,
                          'err_obs_mag' : cat_source.err_obs_mag,
                          'astrometric_catalog' : frame.astrometric_catalog,
                          'photometric_catalog' : frame.photometric_catalog,
                          'aperture_size' : cat_source.aperture_size,
                          'snr' : cat_source.make_snr(),
                          'flags' : cat_source.map_numeric_to_mpc_flags()
                        }
        source, created = SourceMeasurement.objects.get_or_create(**source_params)
        mpc_line = source.format_mpc_line()
        if persist is not True:
            source.delete()
        return mpc_line

    def handle(self, *args, **options):

        self.stdout.write("==== Light curve building %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))

        try:
            block = Block.objects.get(id=options['blocknum'])
        except Block.DoesNotExist:
            self.stdout.write("Cannot find Block# %d" % options['blocknum'])
            exit(-1)

        self.stdout.write("Analyzing Block# %d for %s" % (block.id, block.body.current_name()))

        frames = Frame.objects.filter(block=block.id, zeropoint__isnull=False, frametype__in=[Frame.BANZAI_QL_FRAMETYPE, Frame.BANZAI_RED_FRAMETYPE]).order_by('midpoint')
        self.stdout.write("Found %d frames for Block# %d with good ZPs" % (len(frames), block.id))
        self.stdout.write("Searching within %.1f arcseconds and +/-%.1f delta magnitudes" % (options['boxwidth'], options['deltamag']))

        if len(frames) != 0:
            elements = model_to_dict(block.body)

            times = []
            mags = []
            mag_errs = []
            mpc_lines = []
            for frame in frames:
                emp_line = compute_ephem(frame.midpoint, elements, frame.sitecode)
                ra  = emp_line[1]
                dec = emp_line[2]
                mag_estimate = emp_line[3]
                (ra_string, dec_string) = radec2strings(ra, dec, ' ')
                sources = search_box(frame, ra, dec, options['boxwidth'])
                midpoint_string = frame.midpoint.strftime('%Y-%m-%d %H:%M:%S')
                self.stdout.write("%s %s %s V=%.1f %s (%d) %s" % (midpoint_string, ra_string, dec_string, mag_estimate, frame.sitecode, len(sources), frame.filename))
                if len(sources) != 0:
                    if len(sources) == 1:
                        best_source = sources[0]
    #                    print("%.3f+/-%.3f" % (source.obs_mag, source.err_obs_mag))
                    elif len(sources) > 1:
                        min_sep = options['boxwidth'] * options['boxwidth']
                        best_source = None
                        for source in sources:
                            sep = S.sla_dsep(ra, dec, radians(source.obs_ra), radians(source.obs_dec))
                            sep = degrees(sep) * 3600.0
                            src_ra_string, src_dec_string = radec2strings(radians(source.obs_ra), radians(source.obs_dec))
                            delta_mag = abs(mag_estimate - source.obs_mag)
                            self.stdout.write("%s %s %s %s %.1f %.1f-%.1f %.1f" % ( ra_string, dec_string, src_ra_string, src_dec_string, sep, mag_estimate, source.obs_mag, delta_mag))
                            if sep < min_sep and delta_mag <= options['deltamag']:
                                min_sep = sep
                                best_source = source

                    if best_source and best_source.obs_mag > 0.0:
                        mpc_line = self.make_source_measurement(block.body, frame, best_source, persist=False)
                        mpc_lines.append(mpc_line)
                        times.append(frame.midpoint)
                        mags.append(best_source.obs_mag)
                        mag_errs.append(best_source.err_obs_mag)

            self.stdout.write("Found matches in %d of %d frames" % ( len(times), len(frames)))

            # Write light curve data out in similar format to Make_lc.csh
            i = 0
            lightcurve_file = open('lightcurve_data.txt', 'w')
            mpc_file = open('mpc_positions.txt', 'w')

            # Calculate integer part of JD for first frame and use this as a
            # constant in case of wrapover to the next day
            if len(times) > 0 and len(mags) > 0:
                mjd_offset = int(datetime2mjd_utc(times[0]))
                for time in times:
                    time_jd = datetime2mjd_utc(time)
                    time_jd_truncated = time_jd - mjd_offset
                    if i == 0:
                        lightcurve_file.write("#MJD-%.1f Mag. Mag. error\n" % mjd_offset)
                    lightcurve_file.write("%7.5lf %6.3lf %5.3lf\n" % (time_jd_truncated, mags[i], mag_errs[i]))
                    i += 1
                lightcurve_file.close()

                for mpc_line in mpc_lines:
                    mpc_file.write(mpc_line + '\n')
                mpc_file.close()

                if options['title'] is None:
                    plot_title = '%s from %s (%s) on %s' % (block.body.current_name(), block.site.upper(), frame.sitecode, block.when_observed.strftime("%Y-%m-%d"))
                else:
                    plot_title = options['title']

                self.plot_timeseries(times, mags, mag_errs, title=plot_title)
            else:
                self.stdout.write("No sources matched.")
