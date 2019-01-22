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
"""

import os
from sys import exit
from datetime import datetime, timedelta, time
from math import degrees, radians, floor
import numpy as np

from django.core.management.base import BaseCommand, CommandError
from django.forms.models import model_to_dict
try:
    import pyslalib.slalib as S
except:
    pass
import matplotlib.pyplot as plt
from matplotlib.dates import HourLocator, DateFormatter
from astropy.stats import LombScargle
import astropy.units as u
from astropy.time import Time
from django.conf import settings

from core.models import Block, Frame, SuperBlock, SourceMeasurement, CatalogSources
from astrometrics.ephem_subs import compute_ephem, radec2strings, moon_alt_az, get_sitepos
from astrometrics.time_subs import datetime2mjd_utc
from photometrics.catalog_subs import search_box, open_fits_catalog


class Command(BaseCommand):

    help = 'Extract lightcurves of a target from a given SuperBlock. Can look back at earlier SuperBlocks for same object if requested.'

    def add_arguments(self, parser):
        parser.add_argument('supblock', type=int, help='SuperBlock (tracking number) to analyze')
        parser.add_argument('-ts', '--timespan', type=float, default=0.0, help='Days prior to referenced SuperBlock that should be included')
        parser.add_argument('-bw', '--boxwidth', type=float, default=5.0, help='Boxwidth in arcsec to search')
        parser.add_argument('-dm', '--deltamag', type=float, default=0.5, help='delta magnitude tolerance for multiple matches')
        parser.add_argument('--title', type=str, default=None, help='plot title')
        parser.add_argument('--persist', action="store_true", default=False, help='Whether to store cross-matches as SourceMeasurements for the body')
        parser.add_argument('--single', action="store_true", default=False, help='Whether to only analyze a single SuperBlock')
        base_dir = os.path.join(settings.DATA_ROOT, 'Reduction')
        parser.add_argument('--datadir', default=base_dir, help='Place to save data (e.g. %s)' % base_dir)

    def plot_timeseries(self, times, alltimes, mags, mag_errs, zps, zp_errs, fwhm, air_mass, colors='r', title='', sub_title='', datadir='./', super_block=''):
        fig, (ax0, ax1) = plt.subplots(nrows=2, sharex=True, gridspec_kw={'height_ratios': [15, 4]})
        ax0.errorbar(times, mags, yerr=mag_errs, marker='.', color=colors, linestyle=' ')
        ax1.errorbar(times, zps, yerr=zp_errs, marker='.', color=colors, linestyle=' ')
        ax0.invert_yaxis()
        ax1.invert_yaxis()
        ax1.set_xlabel('Time')
        ax0.set_ylabel('Magnitude')
        ax1.set_ylabel('Magnitude')
        fig.suptitle(title)
        ax0.set_title(sub_title)
        ax1.set_title('Zero Point', size='medium')
        ax0.minorticks_on()
        ax1.minorticks_on()
        ax0.xaxis.set_major_formatter(DateFormatter('%m/%d %H:%M:%S'))
        ax0.fmt_xdata = DateFormatter('%m/%d %H:%M:%S')
        ax1.xaxis.set_major_formatter(DateFormatter('%m/%d %H:%M:%S'))
        ax1.fmt_xdata = DateFormatter('%m/%d %H:%M:%S')
        fig.autofmt_xdate()
        try:
            obj_name = super_block.current_name().replace(' ', '_')
            tn = super_block.tracking_number
        except AttributeError:
            obj_name = 'UNKNOWN'
            tn = 'NNN'
        fig.savefig(os.path.join(datadir, '{}_{}_lightcurve.png'.format(obj_name, tn)))

        fig2, (ax2, ax3) = plt.subplots(nrows=2, sharex=True)
        ax2.plot(alltimes, fwhm, marker='.', color=colors, linestyle=' ')
        ax2.set_ylabel('FWHM (")')
        # ax2.set_title('FWHM')
        fig2.suptitle('Conditions for obs: '+title)
        ax3.plot(alltimes, air_mass, marker='.', color=colors, linestyle=' ')
        ax3.set_xlabel('Time')
        ax3.set_ylabel('Airmass')
        # ax3.set_title('Airmass')
        ax2.minorticks_on()
        ax3.minorticks_on()
        ax3.invert_yaxis()
        ax2.xaxis.set_major_formatter(DateFormatter('%m/%d %H:%M:%S'))
        ax2.fmt_xdata = DateFormatter('%m/%d %H:%M:%S')
        ax3.xaxis.set_major_formatter(DateFormatter('%m/%d %H:%M:%S'))
        ax3.fmt_xdata = DateFormatter('%m/%d %H:%M:%S')
        fig2.autofmt_xdate()
        fig2.savefig(os.path.join(datadir, '{}_{}_lightcurve_cond.png'.format(obj_name, tn)))

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

    def clean_filter(self, filt):
        if len(filt) > 1 and filt[1] == 'p':
            filt = 's'+filt[0]
        return filt.upper()

    def output_alcdef(self, lightcurve_file, block, site, dates, mags, mag_errors, filt):
        obj_name = block.body.current_name()
        mid_time = (dates[-1] - dates[0])/2 + dates[0]
        metadata_dict = {'ObjectNumber': 0,
                         'ObjectName'  : obj_name,
                         'MPCDesig'    : obj_name,
                         'ReviseData'  : 'FALSE',
                         'AllowSharing': 'TRUE',
                         'MPCCode'     : site,
                         'Delimiter'   : 'PIPE',
                         'ContactInfo' : '[{}]'.format(block.proposal.pi),
                         'ContactName' : 'T. Lister',
                         'DifferMags'  : 'FALSE',
                         'Facility'    : 'Las Cumbres Observatory',
                         'Filter'      : self.clean_filter(filt),
                         'LTCApp'      : 'NONE',
                         'LTCType'     : 'NONE',
                         'MagBand'     : 'GG',
                         'Observers'   : 'T. Lister; J. Chatelain; E. Gomez',
                         'ReducedMags' : 'NONE',
                         'SessionDate' : mid_time.strftime('%Y-%m-%d'),
                         'SessionTime' : mid_time.strftime('%H:%M:%S')
                        }
        if obj_name.isdigit():
            metadata_dict['ObjectNumber'] = obj_name
            metadata_dict['MPCDesig'] = block.body.old_name()
            metadata_dict['ObjectName'] = block.body.old_name()
        lightcurve_file.write('STARTMETADATA\n')
        for key, value in metadata_dict.items():
            lightcurve_file.write('{}={}\n'.format(key.upper(), value))
        lightcurve_file.write('ENDMETADATA\n')
        i = 0
        for date in dates:
            jd = datetime2mjd_utc(date)+2400000.5
            lightcurve_file.write('DATA={:.6f}|{:+.3f}|{:+.3f}\n'.format(jd, mags[i], mag_errors[i]))
            i += 1
        lightcurve_file.write('ENDDATA\n')

    def handle(self, *args, **options):

        self.stdout.write("==== Light curve building %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))

        try:
            start_super_block = SuperBlock.objects.get(tracking_number=options['supblock'])
        except SuperBlock.DoesNotExist:
            self.stdout.write("Cannot find SuperBlock with Tracking Number %d" % options['supblock'])
            exit(-1)
        start_blocks = Block.objects.filter(superblock=start_super_block.id)
        start_block = start_blocks[0]
        if options['single'] is True:
            super_blocks = [start_super_block, ]
        else:
            super_blocks = SuperBlock.objects.filter(body=start_super_block.body, block_start__gte=start_super_block.block_start-timedelta(days=options['timespan']))

        times = []
        alltimes = []
        mags = []
        mag_errs = []
        zps = []
        zp_errs = []
        mpc_lines = []
        total_frame_count = 0
        mpc_site = []
        fwhm = []
        air_mass = []
        obj_name = start_super_block.body.current_name().replace(' ', '_')
        datadir = os.path.join(options['datadir'], obj_name)
        if not os.path.exists(datadir):
            try:
                os.makedirs(datadir)
            except:
                msg = "Error creating output path %s" % data_dir
                raise CommandError(msg)
        filename = os.path.join(datadir, '{}_{}_ALCDEF.txt'.format(obj_name, start_super_block.tracking_number))
        alcdef_file = open(filename, 'w')
        for super_block in super_blocks:
            block_list = Block.objects.filter(superblock=super_block.id)
            self.stdout.write("Analyzing SuperblockBlock# %s for %s" % (super_block.tracking_number, super_block.body.current_name()))

            for block in block_list:
                block_mags = []
                block_mag_errs = []
                block_times = []
                self.stdout.write("Analyzing Block# %d" % block.id)

                obs_site = block.site
                frames_red = Frame.objects.filter(block=block.id, frametype__in=[Frame.BANZAI_RED_FRAMETYPE]).order_by('midpoint')
                frames_ql = Frame.objects.filter(block=block.id, frametype__in=[Frame.BANZAI_QL_FRAMETYPE]).order_by('midpoint')
                if len(frames_red) >= len(frames_ql):
                    frames_all_zp = frames_red
                else:
                    frames_all_zp = frames_ql
                frames = frames_all_zp.filter(zeropoint__isnull=False)
                self.stdout.write("Found %d frames (of %d total) for Block# %d with good ZPs" % (frames.count(), frames_all_zp.count(), block.id))
                self.stdout.write("Searching within %.1f arcseconds and +/-%.1f delta magnitudes" % (options['boxwidth'], options['deltamag']))
                total_frame_count += frames.count()
                if frames_all_zp.count() != 0:
                    elements = model_to_dict(block.body)
                    filter_list = []
                    for frame in frames_all_zp:
                        emp_line = compute_ephem(frame.midpoint, elements, frame.sitecode)
                        ra = emp_line[1]
                        dec = emp_line[2]
                        mag_estimate = emp_line[3]
                        (ra_string, dec_string) = radec2strings(ra, dec, ' ')
                        sources = search_box(frame, ra, dec, options['boxwidth'])
                        midpoint_string = frame.midpoint.strftime('%Y-%m-%d %H:%M:%S')
                        self.stdout.write("%s %s %s V=%.1f %s (%d) %s" % (midpoint_string, ra_string, dec_string, mag_estimate, frame.sitecode, len(sources), frame.filename))
                        best_source = None
                        if len(sources) != 0 and frame.zeropoint is not None:
                            if len(sources) == 1:
                                best_source = sources[0]
                            elif len(sources) > 1:
                                min_sep = options['boxwidth'] * options['boxwidth']
                                for source in sources:
                                    sep = S.sla_dsep(ra, dec, radians(source.obs_ra), radians(source.obs_dec))
                                    sep = degrees(sep) * 3600.0
                                    src_ra_string, src_dec_string = radec2strings(radians(source.obs_ra), radians(source.obs_dec))
                                    delta_mag = abs(mag_estimate - source.obs_mag)
                                    self.stdout.write("%s %s %s %s %.1f %.1f-%.1f %.1f" % ( ra_string, dec_string, src_ra_string, src_dec_string, sep, mag_estimate, source.obs_mag, delta_mag))
                                    if sep < min_sep and delta_mag <= 3 * options['deltamag']:
                                        min_sep = sep
                                        best_source = source

                            if best_source and best_source.obs_mag > 0.0 and abs(mag_estimate - best_source.obs_mag) <= 3 * options['deltamag']:
                                block_times.append(frame.midpoint)
                                mpc_line = self.make_source_measurement(block.body, frame, best_source, persist=options['persist'])
                                mpc_lines.append(mpc_line)
                                block_mags.append(best_source.obs_mag)
                                block_mag_errs.append(best_source.err_obs_mag)
                                filter_list.append(frame.filter)
                                zps.append(frame.zeropoint)
                                zp_errs.append(frame.zeropoint_err)
                        # We append these even if we don't have a matching source or zeropoint
                        # so we can plot conditions for all frames
                        alltimes.append(frame.midpoint)
                        fwhm.append(frame.fwhm)
                        azimuth, altitude = moon_alt_az(frame.midpoint, ra, dec, *get_sitepos(frame.sitecode)[1:])
                        zenith_distance = radians(90) - altitude
                        air_mass.append(S.sla_airmas(zenith_distance))
                        obs_site = frame.sitecode
                        if obs_site not in mpc_site:
                            mpc_site.append(obs_site)
                    if len(block_times) > 1:
                        filter_set = list(set(filter_list))
                        for filt in filter_set:
                            mag_set = [m for m, f in zip(block_mags, filter_list) if f == filt]
                            time_set = [t for t, f in zip(block_times, filter_list) if f == filt]
                            error_set = [e for e, f in zip(block_mag_errs, filter_list) if f == filt]
                            self.output_alcdef(alcdef_file, block, obs_site, time_set, mag_set, error_set, filt)
                    mags += block_mags
                    mag_errs += block_mag_errs
                    times += block_times
        alcdef_file.close()
        self.stdout.write("Found matches in %d of %d frames" % ( len(times), total_frame_count))

        # Write light curve data out in similar format to Make_lc.csh
        i = 0
        lightcurve_file = open(os.path.join(datadir, '{}_{}_lightcurve_data.txt'.format(obj_name, start_super_block.tracking_number)), 'w')
        mpc_file = open(os.path.join(datadir, '{}_{}_mpc_positions.txt'.format(obj_name, start_super_block.tracking_number)), 'w')

        # Calculate integer part of JD for first frame and use this as a
        # constant in case of wrapover to the next day
        if len(times) > 0 and len(mags) > 0:
            mjd_offset = int(datetime2mjd_utc(times[0]))
            for time in times:
                time_jd = datetime2mjd_utc(time)
                time_jd_truncated = time_jd - mjd_offset
                if i == 0:
                    lightcurve_file.write('Object: %s\n' % start_super_block.body.current_name())
                    lightcurve_file.write("#MJD-%.1f Mag. Mag. error\n" % mjd_offset)
                lightcurve_file.write("%7.5lf %6.3lf %5.3lf\n" % (time_jd_truncated, mags[i], mag_errs[i]))
                i += 1
            lightcurve_file.close()

            for mpc_line in mpc_lines:
                mpc_file.write(mpc_line + '\n')
            mpc_file.close()

            if options['title'] is None:
                sites = ', '.join(mpc_site)
                try:
                    if options['timespan'] < 1:
                        plot_title = '%s from %s (%s) on %s' % (start_super_block.body.current_name(),
                                                                start_block.site.upper(), sites, start_super_block.block_end.strftime("%Y-%m-%d"))
                        subtitle = ''
                    else:
                        plot_title = '%s from %s to %s' % (start_block.body.current_name(),
                                                           (start_super_block.block_end - timedelta(days=options['timespan'])).strftime("%Y-%m-%d"),
                                                           start_super_block.block_end.strftime("%Y-%m-%d"))
                        subtitle = 'Sites: ' + sites
                except TypeError:
                    plot_title = 'LC for %s' % (start_super_block.body.current_name())
                    subtitle = ''
            else:
                plot_title = options['title']
                subtitle = ''

            self.plot_timeseries(times, alltimes, mags, mag_errs, zps, zp_errs, fwhm, air_mass, title=plot_title, sub_title=subtitle, datadir=datadir, super_block=start_super_block)
        else:
            self.stdout.write("No sources matched.")
