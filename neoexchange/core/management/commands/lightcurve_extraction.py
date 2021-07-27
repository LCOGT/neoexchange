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
import stat
from sys import exit
from datetime import datetime, timedelta, time
from math import degrees, radians, floor
import numpy as np
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.forms.models import model_to_dict
try:
    import pyslalib.slalib as S
except:
    pass
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.dates import HourLocator, DateFormatter
from astropy.stats import LombScargle
import astropy.units as u
from astropy.time import Time
from django.conf import settings
from core.models import Block, Frame, SuperBlock, SourceMeasurement, CatalogSources
from astrometrics.ephem_subs import compute_ephem, radec2strings, moon_alt_az, get_sitepos
from astrometrics.time_subs import datetime2mjd_utc
from photometrics.gf_movie import make_gif
from photometrics.catalog_subs import search_box, sanitize_object_name
from photometrics.photometry_subs import compute_fwhm, map_filter_to_wavelength
from core.archive_subs import make_data_dir


class Command(BaseCommand):

    help = 'Extract lightcurves of a target from a given SuperBlock. Can look back at earlier SuperBlocks for same object if requested.'

    def add_arguments(self, parser):
        parser.add_argument('supblock', type=int, help='SuperBlock (tracking number) to analyze')
        parser.add_argument('-ts', '--timespan', type=float, default=0.0, help='Days prior to referenced SuperBlock that should be included')
        parser.add_argument('-bw', '--boxwidth', type=float, default=5.0, help='Box half-width in arcsec to search')
        parser.add_argument('-dm', '--deltamag', type=float, default=0.5, help='delta magnitude tolerance for multiple matches')
        parser.add_argument('--title', type=str, default=None, help='plot title')
        parser.add_argument('--persist', action="store_true", default=False, help='Whether to store cross-matches as SourceMeasurements for the body')
        parser.add_argument('--single', action="store_true", default=False, help='Whether to only analyze a single SuperBlock')
        parser.add_argument('--nogif', action="store_true", default=False, help='Whether to create a gif movie of the extraction')
        parser.add_argument('--date', action="store", default=None, help='Date of the blocks to extract (YYYYMMDD)')
        base_dir = os.path.join(settings.DATA_ROOT, 'Reduction')
        parser.add_argument('--datadir', default=base_dir, help='Place to save data (e.g. %s)' % base_dir)

    def generate_expected_fwhm(self, times, airmasses, fwhm_0=2.0, obs_filter='w', tel_diameter=0.4*u.m):
        """Compute the expected FWHM and the variation with airmass and observing
        wavelength. Assumes the first value of FWHM (fwhm_0, in arcsec) is
        representative and converts it to seeing.
        Returns a list of expected FWHM values (in arcsec but not as Quantity's
        for easier plotting)"""

        expected_fwhm = []
        filter_cwave = map_filter_to_wavelength(obs_filter)
        # Convert first value of FWHM to seeing by correcting to airmass 1.0 and 500nm
        seeing = fwhm_0 / (airmasses[0]**0.6)
        seeing /= ((filter_cwave.to(u.nm) / (500.0*u.nm))**-0.2)
        seeing *= u.arcsec
        msg = "Initial FWHM, seeing= {:.3f} {:.3f} {}".format(fwhm_0, seeing.value, seeing.unit)
        self.stdout.write(msg)

        for time, airmass in zip(times, airmasses):
            tic_params = {  'seeing' : seeing,
                            'airmass' : airmass,
                            'wavelength' : filter_cwave,
                            'm1_diameter' : tel_diameter}
            fwhm = compute_fwhm(tic_params)
            expected_fwhm.append(fwhm.value)

        return expected_fwhm

    def plot_timeseries(self, times, alltimes, mags, mag_errs, zps, zp_errs, fwhm, air_mass, colors='r', title='', sub_title='', datadir='./', filename='tmp_', diameter=0.4*u.m):
        """Uses matplotlib to create and save a quick LC plot png as well as a sky conditions plot png.

        Parameters
        ----------
        times : [DateTime]
            Times of frames with properly extracted source for target
        alltimes: [DateTime]
            Complete list of times for all frames
        mags : [Float]
            Extracted magnitudes for target (Same Length as `times`)
        mag_errs : [Float]
            Extracted magnitude errors for target (Same Length as `times`)
        zps : [Float]
            Total list of zero points for all frames (Same Length as `alltimes`)
        zps_errs : [Float]
            Total list of zero point errors for all frames (Same Length as `alltimes`)
        fwhm : [Float]
            Total list of mean fwhm for all frames (Same Length as `alltimes`)
        air_mass : [Float]
            Total list of airmass for all frames (Same Length as `alltimes`)
        colors : str
            text representing color recognizable to matplotlib --> changes default color of all plots.
        title : str
            text of plot titles
        sub_title : str
            text of plot subtitle
        datadir : str
            path in which to save the plots
        filename : str
            basename for plots
        diameter : Float * Units.length
            Telescope diameter
        """
        # Build Figure
        fig, (ax0, ax1) = plt.subplots(nrows=2, sharex=True, gridspec_kw={'height_ratios': [15, 4]})
        # Plot LC
        ax0.errorbar(times, mags, yerr=mag_errs, marker='.', color=colors, linestyle=' ')
        # Sort out/Plot good Zero Points
        zp_times = [alltimes[i] for i, zp in enumerate(zps) if zp and zp_errs[i]]
        zps_good = [zp for i, zp in enumerate(zps) if zp and zp_errs[i]]
        zp_errs_good = [zp_errs[i] for i, zp in enumerate(zps) if zp and zp_errs[i]]
        ax1.errorbar(zp_times, zps_good, yerr=zp_errs_good, marker='.', color=colors, linestyle=' ')
        # Set up Axes/Titles
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

        date_string = self.format_date(times)
        ax0.xaxis.set_major_formatter(DateFormatter(date_string))
        ax0.fmt_xdata = DateFormatter(date_string)
        ax1.xaxis.set_major_formatter(DateFormatter(date_string))
        ax1.fmt_xdata = DateFormatter(date_string)
        fig.autofmt_xdate()

        fig.savefig(os.path.join(datadir, filename + 'lightcurve.png'))

        # Build Conditions plot
        fig2, (ax2, ax3) = plt.subplots(nrows=2, sharex=True)
        ax2.plot(alltimes, fwhm, marker='.', color=colors, linestyle=' ')
        expected_fwhm = self.generate_expected_fwhm(alltimes, air_mass, fwhm_0=fwhm[0], tel_diameter=diameter)
        if (times[-1] - times[0]) < timedelta(hours=12):
            ax2.plot(alltimes, expected_fwhm, color='black', linestyle='--', linewidth=0.75, label="Predicted")
        else:
            ax2.plot(alltimes, expected_fwhm, color='black', linestyle=' ', marker='+', markersize=2, label="Predicted")

        # Set up Axes/Titles
        ax2.set_ylabel('FWHM (")')
        # ax2.set_title('FWHM')
        fig2.suptitle('Conditions for obs: '+title)
        ax2.set_title(sub_title)
        ax3.plot(alltimes, air_mass, marker='.', color=colors, linestyle=' ')
        ax3.set_xlabel('Time')
        ax3.set_ylabel('Airmass')
        # ax3.set_title('Airmass')
        ax2.minorticks_on()
        ax3.minorticks_on()
        ax3.invert_yaxis()
        ax2.xaxis.set_major_formatter(DateFormatter(date_string))
        ax2.fmt_xdata = DateFormatter(date_string)
        ax3.xaxis.set_major_formatter(DateFormatter(date_string))
        ax3.fmt_xdata = DateFormatter(date_string)
        fig2.autofmt_xdate()
        ax2.legend()
        fig2.savefig(os.path.join(datadir, filename + 'lightcurve_cond.png'))

        return

    def format_date(self, dates):
        """
        Adjust Date format based on length of timeseries

        :param dates: [DateTime]
        :return: str -- DateTime format
        """
        start = dates[0]
        end = dates[-1]
        time_diff = end - start
        if time_diff > timedelta(days=3):
            return "%Y/%m/%d"
        elif time_diff > timedelta(hours=6):
            return "%m/%d %H:%M"
        elif time_diff > timedelta(minutes=30):
            return "%H:%M"
        else:
            return "%H:%M:%S"

    def make_source_measurement(self, body, frame, cat_source, persist=False):
        """
        Save Source measurement to DB and create corresponding MPC and ADES outputs.

        :param body: Body object
        :param frame: Frame Object
        :param cat_source: CatalogSource Object -- Target (hopefully)
        :param persist: bool -- Whether to keep or destroy source once created.
        :return: mpc_line, ades_psv_line -- properly formatted text lines for the source measurement
        """
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

        ades_psv_line = source.format_psv_line()
        if persist is not True:
            source.delete()
        return mpc_line, ades_psv_line

    def output_alcdef(self, lightcurve_file, block, site, dates, mags, mag_errors, filt, outmag):
        """
        Create a standardized ALCDEF formatted text file for LC data

        :param lightcurve_file: Open file object
        :param block: Block object
        :param site: str -- MPC Site code
        :param dates: [DateTime] -- times of obs
        :param mags: [Float] -- Magnitudes from obs
        :param mag_errors: [Float] -- Magnitude Errors
        :param filt: str -- Filter used during observation
        :param outmag: str -- Filter converted to during reduction
        :return: None
        """
        obj_name = block.body.current_name()

        mid_time = (dates[-1] - dates[0])/2 + dates[0]
        metadata_dict = {'ObjectNumber': 0,
                         'ObjectName'  : obj_name,
                         'MPCDesig'    : obj_name,
                         'ReviseData'  : 'FALSE',
                         'AllowSharing': 'TRUE',
                         'MPCCode'     : site,
                         'Delimiter'   : 'PIPE',
                         'ContactInfo' : '[{}]'.format(block.superblock.proposal.pi),
                         'ContactName' : 'T. Lister',
                         'DifferMags'  : 'FALSE',
                         'Facility'    : 'Las Cumbres Observatory',
                         'Filter'      : filt,
                         'LTCApp'      : 'NONE',
                         'LTCType'     : 'NONE',
                         'MagBand'     : outmag,
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
            jd = datetime2mjd_utc(date)+0.5
            lightcurve_file.write('DATA=24{:.6f}|{:+.3f}|{:+.3f}\n'.format(jd, mags[i], mag_errors[i]))
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
        obs_date = None
        if options['date']:
            if isinstance(options['date'], str):
                try:
                    obs_date = datetime.strptime(options['date'], '%Y%m%d')
                except ValueError:
                    raise CommandError(usage)
            else:
                obs_date = options['date']

        # Initialize lists
        times = []
        alltimes = []
        mags = []
        mag_errs = []
        zps = []
        zp_errs = []
        mpc_lines = []
        psv_lines = []
        total_frame_count = 0
        mpc_site = []
        fwhm = []
        air_mass = []
        output_file_list = []

        # build directory path / set permissions
        obj_name = sanitize_object_name(start_super_block.body.current_name())
        datadir = os.path.join(options['datadir'], obj_name)
        out_path = settings.DATA_ROOT
        data_path = ''
        rw_permissions = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH
        if not os.path.exists(datadir) and not settings.USE_S3:
            try:
                os.makedirs(datadir)
                # Set directory permissions correctly for shared directories
                # Sets to (r)ead,(w)rite,e(x)ecute for owner & group, r-x for others
                os.chmod(datadir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)
            except:
                msg = "Error creating output path %s" % datadir
                raise CommandError(msg)
        sb_day = start_super_block.block_start.strftime("%Y%m%d")
        sb_site = start_super_block.get_sites().replace(',', '')

        # Turn telescope class into a diameter for theoretical FWHM curve
        tel_classes = start_super_block.get_telclass()
        if len(tel_classes.split(",")) > 1:
            self.stdout.write("Multiple telescope sizes found; theoretical FWHM curve will be wrong")
            tel_class = tel_classes.split(",")[0]
        else:
            tel_class = tel_classes
        try:
            tel_diameter = float(tel_class.replace('m', '.'))
            tel_diameter *= u.m
        except ValueError:
            self.stdout.write("Error determining telescope diameter, assuming 0.4m")
            tel_diameter = 0.4*u.m

        # Create, name, open ALCDEF file.
        if obs_date:
            alcdef_date = options['date']
        else:
            alcdef_date = sb_day
        base_name = '{}_{}_{}_{}_'.format(obj_name, sb_site, alcdef_date, start_super_block.tracking_number)
        alcdef_filename = os.path.join(datadir, base_name + 'ALCDEF.txt')
        output_file_list.append('{},{}'.format(alcdef_filename, datadir.lstrip(out_path)))
        alcdef_file = default_storage.open(alcdef_filename, 'w')
        for super_block in super_blocks:
            block_list = Block.objects.filter(superblock=super_block.id)
            if obs_date:
                block_list = block_list.filter(when_observed__lt=obs_date+timedelta(days=2)).filter(when_observed__gt=obs_date)
            self.stdout.write("Analyzing SuperblockBlock# %s for %s" % (super_block.tracking_number, super_block.body.current_name()))
            for block in block_list:
                block_mags = []
                block_mag_errs = []
                block_times = []
                outmag = "NONE"
                self.stdout.write("Analyzing Block# %d" % block.id)

                obs_site = block.site
                # Get all Useful frames from each block
                frames_red = Frame.objects.filter(block=block.id, frametype__in=[Frame.BANZAI_RED_FRAMETYPE]).order_by('filter', 'midpoint')
                frames_ql = Frame.objects.filter(block=block.id, frametype__in=[Frame.BANZAI_QL_FRAMETYPE]).order_by('filter', 'midpoint')
                if len(frames_red) >= len(frames_ql):
                    frames_all_zp = frames_red
                else:
                    frames_all_zp = frames_ql
                frames = frames_all_zp.filter(zeropoint__isnull=False)
                self.stdout.write("Found %d frames (of %d total) for Block# %d with good ZPs" % (frames.count(), frames_all_zp.count(), block.id))
                self.stdout.write("Searching within %.1f arcseconds and +/-%.2f delta magnitudes" % (options['boxwidth'], options['deltamag']))
                total_frame_count += frames.count()
                frame_data = []
                if frames_all_zp.count() != 0:
                    elements = model_to_dict(block.body)
                    filter_list = []

                    for frame in frames_all_zp:
                        # get predicted position and magnitude of target during time of each frame
                        emp_line = compute_ephem(frame.midpoint, elements, frame.sitecode)
                        ra = emp_line['ra']
                        dec = emp_line['dec']
                        mag_estimate = emp_line['mag']
                        (ra_string, dec_string) = radec2strings(ra, dec, ' ')
                        # Find list of frame sources within search region of predicted coordinates
                        sources = search_box(frame, ra, dec, options['boxwidth'])
                        midpoint_string = frame.midpoint.strftime('%Y-%m-%d %H:%M:%S')
                        self.stdout.write("%s %s %s V=%.1f %s (%d) %s" % (midpoint_string, ra_string, dec_string, mag_estimate, frame.sitecode, len(sources), frame.filename))
                        best_source = None
                        # Find source most likely to be target (Could Use Some Work)
                        if len(sources) != 0 and frame.zeropoint is not None:
                            if len(sources) == 1:
                                best_source = sources[0]
                            elif len(sources) > 1:  # If more than 1 source, pick closest within deltamag
                                min_sep = options['boxwidth'] * options['boxwidth']
                                for source in sources:
                                    sep = S.sla_dsep(ra, dec, radians(source.obs_ra), radians(source.obs_dec))
                                    sep = degrees(sep) * 3600.0
                                    src_ra_string, src_dec_string = radec2strings(radians(source.obs_ra), radians(source.obs_dec))
                                    if len(block_mags) > 0:
                                        delta_mag = abs(block_mags[-1] - source.obs_mag)
                                    else:
                                        delta_mag = abs(mag_estimate - source.obs_mag)
                                    self.stdout.write("%s %s %s %s %.1f %.1f-%.1f %.1f" % ( ra_string, dec_string, src_ra_string, src_dec_string, sep, mag_estimate, source.obs_mag, delta_mag))
                                    if sep < min_sep and delta_mag <= options['deltamag']:
                                        min_sep = sep
                                        best_source = source

                            # Save target source and add to output files.
                            if best_source and best_source.obs_mag > 0.0 and abs(mag_estimate - best_source.obs_mag) <= 3 * options['deltamag']:
                                block_times.append(frame.midpoint)
                                mpc_line, psv_line = self.make_source_measurement(block.body, frame, best_source, persist=options['persist'])
                                mpc_lines.append(mpc_line)
                                psv_lines.append(psv_line)
                                block_mags.append(best_source.obs_mag)
                                block_mag_errs.append(best_source.err_obs_mag)
                                filter_list.append(frame.ALCDEF_filter_format())

                        # We append these even if we don't have a matching source or zeropoint
                        # so we can plot conditions for all frames
                        zps.append(frame.zeropoint)
                        zp_errs.append(frame.zeropoint_err)
                        frame_data.append({'ra': ra,
                                           'dec': dec,
                                           'mag': mag_estimate,
                                           'bw': options['boxwidth'],
                                           'dm': options['deltamag'],
                                           'best_source': best_source})
                        alltimes.append(frame.midpoint)
                        fwhm.append(frame.fwhm)
                        azimuth, altitude = moon_alt_az(frame.midpoint, ra, dec, *get_sitepos(frame.sitecode)[1:])
                        zenith_distance = radians(90) - altitude
                        air_mass.append(S.sla_airmas(zenith_distance))
                        obs_site = frame.sitecode
                        catalog = frame.photometric_catalog
                        if catalog == 'GAIA-DR2':
                            outmag = 'GG'
                        elif catalog == 'UCAC4':
                            outmag = 'SR'
                        if obs_site not in mpc_site:
                            mpc_site.append(obs_site)
                    if len(block_times) > 1:
                        filter_set = list(set(filter_list))
                        for filt in filter_set:
                            mag_set = [m for m, f in zip(block_mags, filter_list) if f == filt]
                            time_set = [t for t, f in zip(block_times, filter_list) if f == filt]
                            error_set = [e for e, f in zip(block_mag_errs, filter_list) if f == filt]
                            self.output_alcdef(alcdef_file, block, obs_site, time_set, mag_set, error_set, filt, outmag)
                    mags += block_mags
                    mag_errs += block_mag_errs
                    times += block_times

                    # Create gif of fits files used for LC extraction
                    data_path = make_data_dir(out_path, model_to_dict(frames_all_zp[0]))
                    frames_list = [os.path.join(data_path, f.filename) for f in frames_all_zp]
                    if not options['nogif']:
                        movie_file = make_gif(frames_list, sort=False, init_fr=100, center=3, out_path=out_path, plot_source=True,
                                              target_data=frame_data, show_reticle=True, progress=True)
                        if "WARNING" not in movie_file:
                            output_file_list.append('{},{}'.format(movie_file, data_path.lstrip(out_path)))
                            self.stdout.write("New gif created: {}".format(movie_file))
                        else:
                            self.stdout.write(movie_file)
        alcdef_file.close()
        self.stdout.write("Found matches in %d of %d frames" % (len(times), total_frame_count))

        if not settings.USE_S3:
            try:
                os.chmod(alcdef_filename, rw_permissions)
            except PermissionError:
                pass

            # Write light curve data out in similar format to Make_lc.csh
            i = 0

            lightcurve_file = open(os.path.join(datadir, base_name + 'lightcurve_data.txt'), 'w')
            mpc_file = open(os.path.join(datadir, base_name + 'mpc_positions.txt'), 'w')
            psv_file = open(os.path.join(datadir, base_name + 'ades_positions.psv'), 'w')
            output_file_list.append('{},{}'.format(os.path.join(datadir, base_name + 'lightcurve_data.txt'), datadir.lstrip(out_path)))
            output_file_list.append('{},{}'.format(os.path.join(datadir, base_name + 'mpc_positions.txt'), datadir.lstrip(out_path)))
            output_file_list.append('{},{}'.format(os.path.join(datadir, base_name + 'ades_positions.psv'), datadir.lstrip(out_path)))

            # Calculate integer part of JD for first frame and use this as a
            # constant in case of wrapover to the next day
            if len(times) > 0 and len(mags) > 0:
                mjd_offset = int(datetime2mjd_utc(times[0]))
                for time in times:
                    time_jd = datetime2mjd_utc(time)
                    time_jd_truncated = time_jd - mjd_offset
                    if i == 0:
                        lightcurve_file.write('#Object: %s\n' % start_super_block.body.current_name())
                        lightcurve_file.write("#MJD-%.1f Mag. Mag. error\n" % mjd_offset)
                    lightcurve_file.write("%7.5lf %6.3lf %5.3lf\n" % (time_jd_truncated, mags[i], mag_errs[i]))
                    i += 1
                lightcurve_file.close()
                try:
                    os.chmod(os.path.join(datadir, base_name + 'lightcurve_data.txt'), rw_permissions)
                except PermissionError:
                    pass

                # Write out MPC1992 80 column file
                for mpc_line in mpc_lines:
                    mpc_file.write(mpc_line + '\n')
                mpc_file.close()
                try:
                    os.chmod(os.path.join(datadir, base_name + 'mpc_positions.txt'), rw_permissions)
                except PermissionError:
                    pass

                # Write out ADES Pipe Separated Value file
                for psv_line in psv_lines:
                    psv_file.write(psv_line + '\n')
                psv_file.close()
                try:
                    os.chmod(os.path.join(datadir, base_name + 'ades_positions.psv'), rw_permissions)
                except PermissionError:
                    pass

                # Create Default Plot Title
                if options['title'] is None:
                    sites = ', '.join(mpc_site)
                    try:
                        # for single dates and short site lists, put everything on single line.
                        if options['timespan'] < 1 and len(sites) <= 13:
                            plot_title = '%s from %s (%s) on %s' % (start_super_block.body.current_name(),
                                                                    start_block.site.upper(), sites, start_super_block.block_end.strftime("%Y-%m-%d"))
                            subtitle = ''
                        # for lc covering multiple nights, reformat title
                        elif options['timespan'] < 1:
                            plot_title = '%s from %s to %s' % (start_block.body.current_name(),
                                                               (start_super_block.block_end - timedelta(
                                                                   days=options['timespan'])).strftime("%Y-%m-%d"),
                                                               start_super_block.block_end.strftime("%Y-%m-%d"))
                            subtitle = 'Sites: ' + sites
                        # for single night LC using many sites, put sites on 2nd line.
                        else:
                            plot_title = '%s from %s on %s' % (start_super_block.body.current_name(),
                                                               start_block.site.upper(),
                                                               start_super_block.block_end.strftime("%Y-%m-%d"))
                            subtitle = 'Sites: ' + sites
                    except TypeError:
                        plot_title = 'LC for %s' % (start_super_block.body.current_name())
                        subtitle = ''
                else:
                    plot_title = options['title']
                    subtitle = ''

                # Make plots
                if not settings.USE_S3:
                    self.plot_timeseries(times, alltimes, mags, mag_errs, zps, zp_errs, fwhm, air_mass, title=plot_title, sub_title=subtitle, datadir=datadir, filename=base_name, diameter=tel_diameter)
                    output_file_list.append('{},{}'.format(os.path.join(datadir, base_name + 'lightcurve_cond.png'), datadir.lstrip(out_path)))
                    output_file_list.append('{},{}'.format(os.path.join(datadir, base_name + 'lightcurve.png'), datadir.lstrip(out_path)))
                    try:
                        os.chmod(os.path.join(datadir, base_name + 'lightcurve_cond.png'), rw_permissions)
                    except PermissionError:
                        pass
                    try:
                        os.chmod(os.path.join(datadir, base_name + 'lightcurve.png'), rw_permissions)
                    except PermissionError:
                        pass
            else:
                self.stdout.write("No sources matched.")

            if data_path:
                with open(os.path.join(data_path, base_name + 'lc_file_list.txt'), 'w') as outfut_file_file:
                    outfut_file_file.write('# == Files created by Lightcurve Extraction for {} on {} ==\n'.format(obj_name, sb_day))
                    for output_file in output_file_list:
                        outfut_file_file.write(output_file)
                        outfut_file_file.write('\n')
                self.stdout.write(f"New lc file list created: {os.path.join(data_path, base_name + 'lc_file_list.txt')}")
                try:
                    os.chmod(os.path.join(data_path, base_name + 'lc_file_list.txt'), rw_permissions)
                except PermissionError:
                    pass
