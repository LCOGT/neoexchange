import os
from sys import exit
from datetime import datetime, timedelta
from math import degrees, radians

from django.core.management.base import BaseCommand, CommandError
from django.forms.models import model_to_dict
try:
    import pyslalib.slalib as S
except:
    pass
import matplotlib.pyplot as plt
from matplotlib.dates import HourLocator, DateFormatter

from core.models import Block, Frame, SuperBlock, SourceMeasurement
from astrometrics.ephem_subs import compute_ephem, radec2strings
from astrometrics.time_subs import datetime2mjd_utc
from photometrics.catalog_subs import search_box


class Command(BaseCommand):

    help = 'Extract lightcurves of a target from a given SuperBlock. Can look back at earlier SuperBlocks for same object if requested.'

    def add_arguments(self, parser):
        parser.add_argument('supblock', type=int, help='SuperBlock number (tracking number) to analyze')
        parser.add_argument('-ts', '--timespan', type=float, default=0.0, help='Days prior to referenced SuperBlock that should be included')
        parser.add_argument('-bw', '--boxwidth', type=float, default=5.0, help='Boxwidth in arcsec to search')
        parser.add_argument('-dm', '--deltamag', type=float, default=0.5, help='delta magnitude tolerance for multiple matches')
        parser.add_argument('--title', type=str, default=None, help='plot title')

    def plot_timeseries(self, times, mags, mag_errs, colors='r', title='', sub_title=''):
        fig, ax = plt.subplots()
        ax.plot(times, mags, color=colors, marker='.', linestyle=' ')
        ax.errorbar(times, mags, yerr=mag_errs, color=colors, linestyle=' ')
        ax.invert_yaxis()
        ax.set_xlabel('Time')
        ax.set_ylabel('Magnitude')
        fig.suptitle(title)
        ax.set_title(sub_title)
        ax.minorticks_on()
        ax.xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))
        ax.fmt_xdata = DateFormatter('%H:%M:%S')
        fig.autofmt_xdate()
        plt.savefig("lightcurve.png")
        plt.show()

        return

    def make_source_measurement(self, body, frame, cat_source, persist=False):
        source = SourceMeasurement( body = body,
                                    frame = frame,
                                    obs_ra = cat_source.obs_ra,
                                    obs_dec = cat_source.obs_dec,
                                    obs_mag = cat_source.obs_mag,
                                    err_obs_ra = cat_source.err_obs_ra,
                                    err_obs_dec = cat_source.err_obs_dec,
                                    err_obs_mag = cat_source.err_obs_mag,
                                    astrometric_catalog = frame.astrometric_catalog,
                                    photometric_catalog = frame.photometric_catalog,
                                    aperture_size = cat_source.aperture_size,
                                    snr = cat_source.make_snr(),
                                    flags = cat_source.map_numeric_to_mpc_flags()
                                  )
        source.save()
        mpc_line = source.format_mpc_line()
        if persist is not True:
            source.delete()
        return mpc_line

    def handle(self, *args, **options):

        self.stdout.write("==== Light curve building %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))

        try:
            start_super_block = SuperBlock.objects.get(tracking_number=options['supblock'])
        except SuperBlock.DoesNotExist:
            self.stdout.write("Cannot find SuperBlock# %d" % options['supblock'])
            exit(-1)

        super_blocks = SuperBlock.objects.filter(body=start_super_block.body, block_start__gte=start_super_block.block_start-timedelta(days=options['timespan']))
        times = []
        mags = []
        mag_errs = []
        mpc_lines = []
        total_frame_count = 0
        mpc_site = []
        for super_block in super_blocks:
            block_list = Block.objects.filter(superblock=super_block.id)
            self.stdout.write("Analyzing SuperblockBlock# %s for %s" % (super_block.tracking_number, super_block.body.current_name()))
            for block in block_list:
                self.stdout.write("Analyzing Block# %d" % block.id)

                frames_red = Frame.objects.filter(block=block.id, zeropoint__isnull=False, frametype__in=[Frame.BANZAI_RED_FRAMETYPE]).order_by('midpoint')
                frames_ql = Frame.objects.filter(block=block.id, zeropoint__isnull=False, frametype__in=[Frame.BANZAI_QL_FRAMETYPE]).order_by('midpoint')
                if len(frames_red) >= len(frames_ql):
                    frames = frames_red
                else:
                    frames = frames_ql
                self.stdout.write("Found %d frames for Block# %d with good ZPs" % (len(frames), block.id))
                self.stdout.write("Searching within %.1f arcseconds and +/-%.1f delta magnitudes" % (options['boxwidth'], options['deltamag']))
                total_frame_count += len(frames)
                if len(frames) != 0:
                    elements = model_to_dict(block.body)

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

                            if best_source and best_source.obs_mag > 0.0 and abs(mag_estimate - best_source.obs_mag) <= 2 * options['deltamag']:
                                mpc_line = self.make_source_measurement(block.body, frame, best_source, persist=False)
                                mpc_lines.append(mpc_line)
                                times.append(frame.midpoint)
                                mags.append(best_source.obs_mag)
                                mag_errs.append(best_source.err_obs_mag)
                    if frame.sitecode not in mpc_site:
                        mpc_site.append(frame.sitecode)

        self.stdout.write("Found matches in %d of %d frames" % ( len(times), total_frame_count))

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
                if options['timespan'] < 1:
                    plot_title = '%s from %s (%s) on %s' % (block.body.current_name(), block.site.upper(), frame.sitecode, block.when_observed.strftime("%Y-%m-%d"))
                    subtitle = ''
                else:
                    plot_title = '%s from %s to %s' % (block.body.current_name(), (block.when_observed - timedelta(days=options['timespan'])).strftime("%Y-%m-%d"), block.when_observed.strftime("%Y-%m-%d"))
                    subtitle = 'Sites: ' + ", ".join(mpc_site)
            else:
                plot_title = options['title']
                subtitle = ''

            self.plot_timeseries(times, mags, mag_errs, title=plot_title, sub_title=subtitle)
        else:
            self.stdout.write("No sources matched.")
