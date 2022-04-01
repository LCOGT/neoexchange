"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2022-2022 LCO

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
from datetime import datetime, timedelta
from glob import glob
from sys import exit
import tempfile
from math import cos
import matplotlib.pyplot as plt
from matplotlib.dates import HourLocator, DateFormatter

from django.core.management.base import BaseCommand, CommandError
from astropy.coordinates import SkyCoord, Angle
import astropy.units as u
import numpy as np
import calviacat as cvc

from core.urlsubs import QueryTelemetry, convert_temps_to_table
from astrometrics.ephem_subs import horizons_ephem, MPC_site_code_to_domes
from photometrics.catalog_subs import extract_catalog, open_fits_catalog, FITSTblException

import logging

logger = logging.getLogger('photometrics.catalog_subs.open_fits_catalog')
logger.setLevel(logging.FATAL)
logger = logging.getLogger('photometrics.catalog_subs.extract_catalog')
logger.setLevel(logging.FATAL)



class Command(BaseCommand):

    help = """Perform extraction of photometry on a set of FITS frames.
         """

    def add_arguments(self, parser):
        parser.add_argument('datadir', help='Path to the data to ingest')
        parser.add_argument('target', help='Name of the target (replace spaces with underscores')
        parser.add_argument('-bw', '--boxwidth', type=float, default=3.0, help='Box half-width in arcsec to search')

    def determine_images_and_catalogs(self, datadir, output=True):

        fits_files, fits_catalogs = None, None

        if os.path.exists(datadir) and os.path.isdir(datadir):
            fits_files = sorted(glob(datadir + '*e??.fits'))
            fits_catalogs = sorted(glob(datadir + '*e??_cat.fits'))
            banzai_files = sorted(glob(datadir + '*e91.fits.fz'))
            if len(banzai_files) > 0:
                fits_files = fits_catalogs = banzai_files
            if len(fits_files) == 0 and len(fits_catalogs) == 0:
                self.stdout.write("No FITS files and catalogs found in directory %s" % datadir)
                fits_files, fits_catalogs = None, None
            else:
                self.stdout.write("Found %d FITS files and %d catalogs" % ( len(fits_files), len(fits_catalogs)))
        else:
            self.stdout.write("Could not open directory $s" % datadir)
            fits_files, fits_catalogs = None, None

        return fits_files, fits_catalogs

    def fetch_dimm_seeing(self, sitecode, date):
        seeing = []
        site, encid, telid = MPC_site_code_to_domes(sitecode)
        if site == 'cpt':
            date = date.replace(hour=16, minute=0, second=0)
            date += timedelta(days=1)
        fwhm = QueryTelemetry(start_time=date)
        dimm_data = fwhm.get_seeing_for_site(site)
        if len(dimm_data) > 0:
            tables = convert_temps_to_table(dimm_data, time_field='measure_time', datum_name='seeing', data_field='seeing')
            seeing = tables[0]
        return seeing

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

    def plot_timeseries(self, times, alltimes, mags, mag_errs, seeing, fwhm, colors='r', title='', sub_title='', datadir='./', filename='tmp_'):

        # Build Figure
        fig, (ax0, ax1) = plt.subplots(nrows=2, sharex=True, figsize=(10,7.5), gridspec_kw={'height_ratios': [15, 4]})
        # Plot LC
        ax0.errorbar(times, mags, yerr=mag_errs, marker='.', color=colors, linestyle=' ')
        # Sort out/Plot good Zero Points
        # zp_times = [alltimes[i] for i, zp in enumerate(zps) if zp and zp_errs[i]]
        # zps_good = [zp for i, zp in enumerate(zps) if zp and zp_errs[i]]
        # zp_errs_good = [zp_errs[i] for i, zp in enumerate(zps) if zp and zp_errs[i]]
        # ax1.errorbar(zp_times, zps_good, yerr=zp_errs_good, marker='.', color=colors, linestyle=' ')
        ax1.plot(alltimes, fwhm, marker='.', color=colors, linestyle=' ')

        # Cut down DIMM results to span of Block
        if len(seeing) > 0:
            mask1 = seeing['UTC Datetime'] >= alltimes[0]
            mask2 = seeing['UTC Datetime'] <= alltimes[-1]
            mask = mask1 & mask2
            block_seeing = seeing[mask]
            ax1.plot(block_seeing['UTC Datetime'], block_seeing['seeing'], color='DodgerBlue', linestyle='-', label='DIMM')
        # Set up Axes/Titles
        ax0.invert_yaxis()
#        ax1.invert_yaxis()
        ax1.set_xlabel('Time')
        ax0.set_ylabel('Magnitude')
        ax1.set_ylabel('FWHM (")')
        fig.suptitle(title)
        ax0.set_title(sub_title)
        ax1.set_title('Conditions for obs', size='medium')
        ax0.minorticks_on()
        ax1.minorticks_on()

        date_string = self.format_date(times)
        ax0.xaxis.set_major_formatter(DateFormatter(date_string))
        ax0.fmt_xdata = DateFormatter(date_string)
        ax1.xaxis.set_major_formatter(DateFormatter(date_string))
        ax1.fmt_xdata = DateFormatter(date_string)
        fig.autofmt_xdate()

        fig.savefig(os.path.join(datadir, filename + 'lightcurve.png'))

        return

    def handle(self, *args, **options):

        dbg = False
        self.stdout.write("==== Pipeline processing BANZAI photometry %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))

        datadir = os.path.expanduser(options['datadir'])
        datadir = os.path.join(datadir, '')
        self.stdout.write("datapath= %s" % datadir)

        # Get lists of images and catalogs
        fits_files, fits_catalogs = self.determine_images_and_catalogs(datadir)
        if fits_files is None or fits_catalogs is None:
            exit(-2)

        header, _ = extract_catalog(fits_catalogs[0], 'BANZAI', header_only=True)
        first_frametime = header['obs_date']
        first_frametime = first_frametime.replace(second=0, microsecond=0)
        
        header, _  = extract_catalog(fits_catalogs[-1], 'BANZAI', header_only=True)
        last_frametime = header['obs_date'] + timedelta(seconds=header['exptime'])
        last_frametime = last_frametime.replace(second=0, microsecond=0)
        last_frametime += timedelta(seconds=60)
        self.stdout.write(f"Timespan {first_frametime:} => {last_frametime:}")

        ephem = horizons_ephem(options['target'].replace('_', ' '), first_frametime, last_frametime, header['site_code'], '1m')
        self.stdout.write(f"Ephemeris length= {len(ephem):}")
        failures = {'Bad WCS' : 0,
                    'Bad table' : 0
                   }
        success = 0
        times = []
        alltimes = []
        fwhm = []
        mags = []
        magerrs = []
        zps = []
#        zp = 30.763
        for catalog in fits_catalogs:
            filename = os.path.basename(catalog)
            header, _ = extract_catalog(catalog, 'BANZAI', header_only=True)
            print(f"{filename}: ", end='')
            table = None
            if header and header['astrometric_fit_status'] == 0:
                msg = f"{header['astrometric_fit_status']:>11}"
                try:
                    header, table = extract_catalog(catalog, 'BANZAI')
                except FITSTblException:
                    header = table = None
                    failures['Bad table'] += 1
                    msg = "Bad table"
            else:
                msg = "Bad WCS fit"
                failures['Bad WCS'] += 1

            print(msg, end='')
            if header and table:
                start_time = header['obs_midpoint'] - timedelta(seconds=29)
                end_time = header['obs_midpoint'] + timedelta(seconds=31)
                time_mask = (ephem['datetime'] >= start_time) & (ephem['datetime'] < end_time)
                row = ephem[time_mask][0]
                ra = row['RA']
                dec = row['DEC']
                pos = SkyCoord(ra,dec,unit=u.deg)

                box_halfwidth_deg = Angle(options['boxwidth'], unit=u.arcsec).to(u.deg)
                ra_deg = pos.ra.to(u.deg)
                dec_deg = pos.dec.to(u.deg)
                ra_min = ra_deg - box_halfwidth_deg / cos(pos.dec.to(u.rad).value)
                ra_min = ra_min.value
                ra_max = ra_deg + box_halfwidth_deg / cos(pos.dec.to(u.rad).value)
                ra_max = ra_max.value
                box_dec_min = dec_deg - box_halfwidth_deg
                box_dec_max = dec_deg + box_halfwidth_deg
                dec_min = min(box_dec_min, box_dec_max)
                dec_max = max(box_dec_min, box_dec_max)
                dec_min = dec_min.value
                dec_max = dec_max.value

                if dbg: print("Searching %.4f->%.4f, %.4f->%.4f" % (ra_min, ra_max, dec_min, dec_max))
                obj_mask = (table['obs_ra'] >= ra_min) & (table['obs_ra'] <= ra_max) & (table['obs_dec'] > dec_min) & (table['obs_dec'] < dec_max)
                obj = table[obj_mask]
                obs_mag = -99
                obs_mag_err = -99
                alltimes.append(header['obs_midpoint'])
                fwhm.append(header['fwhm'])
                if len(obj) == 1:
                    ps1 = cvc.PanSTARRS1('175706_20210324_cat.db')
                    phot = table[table['flags'] == 0]  # clean LCO catalog
                    lco = SkyCoord(phot['obs_ra'], phot['obs_dec'], unit='deg')

                    ps1.fetch_field(lco)

                    objids, distances = ps1.xmatch(lco)
                    zp, C, unc, r, gmr, gmi = ps1.cal_color(objids, phot['obs_mag'], 'r', 'g-r')
                    obs_mag = obj['obs_mag'][0] + zp
                    obs_mag_err = obj['obs_mag_err'][0]
                    zps.append(zp)
                    mags.append(obs_mag)
                    magerrs.append(obs_mag_err)
                    times.append(header['obs_midpoint'])
                    success += 1
                else:
                    print("Multiple matches")
                print(f"{header['obs_midpoint'].strftime('%Y-%m-%dT%H:%M:%S'):}")
                print(f"  {row['datetime_str']:} RA={ra:8.5f}, Dec={dec:8.5f} V={row['V']:.1f} obs_mag={obs_mag:.3f}+/-{obs_mag_err:.3f} ZP={zp:.3f}+/-{unc:.3f}")
            else:
                print()
        total_frames = len(fits_catalogs)
        print(f"\n{success} frames out of {total_frames} ({success/total_frames:.2%}) succeeded ({failures['Bad WCS']}/{failures['Bad WCS']/total_frames:.2%} WCS failure, {failures['Bad table']}/{failures['Bad table']/total_frames:.2%} catalog problems)")
        zp = np.mean(ephem['V']) - np.mean(mags)
        print(f"ZP={zp:.3f} {np.mean(zps):.3f}")
        plot_title = '%s from %s to %s' % (options['target'],
                                           first_frametime.strftime("%Y-%m-%d"),
                                           last_frametime.strftime("%Y-%m-%d"))
        subtitle = 'Sites: ' + header['site_code']
        seeing = self.fetch_dimm_seeing(header['site_code'], first_frametime)

        self.plot_timeseries(times, alltimes, mags, magerrs, seeing, fwhm, title=plot_title, sub_title=subtitle, datadir=datadir)
