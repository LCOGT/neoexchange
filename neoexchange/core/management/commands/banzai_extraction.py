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
import warnings
import matplotlib.pyplot as plt
from matplotlib.dates import HourLocator, DateFormatter

from django.core.management.base import BaseCommand, CommandError
from astropy.time import Time
from astropy.coordinates import SkyCoord, Angle
import astropy.units as u
import numpy as np
import calviacat as cvc
from scipy.interpolate import interp1d

from core.plots import plot_timeseries
from core.urlsubs import fetch_dimm_seeing
from astrometrics.ephem_subs import horizons_ephem
from photometrics.catalog_subs import extract_catalog, open_fits_catalog, existing_catalog_coverage, FITSTblException

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
        parser.add_argument('target', help='Name of the target (replace spaces with underscores)')
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

    def handle(self, *args, **options):

        dbg = False
        cat_name = 'PS1'
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
                    'Bad table' : 0,
                    'No match' : 0
                   }
        nomatch_files = []
        success = 0
        times = []
        alltimes = []
        fwhm = []
        mags = []
        magerrs = []
        zps = []
        zp_errs = []
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
                start_time = header['obs_midpoint'] - timedelta(seconds=90)
                end_time = header['obs_midpoint'] + timedelta(seconds=90)
                time_mask = (ephem['datetime'] >= start_time) & (ephem['datetime'] <= end_time)
                rows = ephem[time_mask]
#                print('  num rows=',len(rows), start_time, header['obs_midpoint'], end_time)
                row = ephem[time_mask][0]
                # Interpolate RA and Dec to frametime; other values can stay at the closest minute
                f = interp1d(rows['datetime_jd'], rows['RA'])
                t = Time(header['obs_midpoint'])
                ra = f(t.jd)
                f = interp1d(rows['datetime_jd'], rows['DEC'])
                t = Time(header['obs_midpoint'])
                dec = f(t.jd)
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
                zp = -99
                unc = -99
                alltimes.append(header['obs_midpoint'])
                fwhm.append(header['fwhm'])
                if len(obj) == 1:
                    db_filename = existing_catalog_coverage(datadir, header['field_center_ra'], header['field_center_dec'], header['field_width'], header['field_height'], cat_name, dbg)
                    created = False
                    if db_filename is None:
                        # Add 25% to passed width and height in lieu of actual calculation of extent
                        # of a series of frames
                        set_width = header['field_width']
                        set_height = header['field_height']
                        units = set_width[-1]
                        try:
                            ref_width = float(set_width[:-1]) * 1.25
                            ref_width = "{:.4f}{}".format(ref_width, units)
                        except ValueError:
                            ref_width = set_width
                        units = set_height[-1]
                        try:
                            ref_height = float(set_height[:-1]) * 1.25
                            ref_height = "{:.4f}{}".format(ref_height, units)
                        except ValueError:
                            ref_height = set_height

                        # Rewrite name of catalog to include position and size
                        refcat = "{}_{ra:.2f}{dec:+.2f}_{width}x{height}.cat".format(cat_name, ra=header['field_center_ra'], dec=header['field_center_dec'], width=ref_width, height=ref_height)
                        db_filename = os.path.join(datadir, refcat)
                        created = True
                    print(f"  catalog={os.path.basename(db_filename):} (created={created:})", end='')
                    ps1 = cvc.PanSTARRS1(db_filename)
                    phot = table[table['flags'] == 0]  # clean LCO catalog
                    lco = SkyCoord(phot['obs_ra'], phot['obs_dec'], unit='deg')

                    if len(ps1.search(lco)[0]) < 500:
                        ps1.fetch_field(lco)

                    objids, distances = ps1.xmatch(lco)
                    with warnings.catch_warnings():
                        warnings.filterwarnings("ignore", message='divide by zero encountered')
                        zp, C, unc, r, gmr, gmi = ps1.cal_color(objids, phot['obs_mag'], 'r', 'g-r')
                    obs_mag = obj['obs_mag'][0] + zp
                    obs_mag_err = obj['obs_mag_err'][0]
                    zps.append(zp)
                    zp_errs.append(unc)
                    mags.append(obs_mag)
                    magerrs.append(obs_mag_err)
                    times.append(header['obs_midpoint'])
                    success += 1
                elif len(obj) == 0:
                    print("No matches")
                    failures['No match'] += 1
                    nomatch_files.append(catalog)
                else:
                    print("Multiple matches", len(obj))

                print(f"  {header['obs_midpoint'].strftime('%Y-%m-%dT%H:%M:%S'):}")
                print(f"  {row['datetime'].strftime('%Y-%m-%d %H:%M'):} RA={ra:8.5f}, Dec={dec:8.5f} V={row['V']:.1f} obs_mag={obs_mag:.3f}+/-{obs_mag_err:.3f} ZP={zp:.3f}+/-{unc:.3f}")
            else:
                print()
        total_frames = len(fits_catalogs)
        print(f"\n{success} frames out of {total_frames} ({success/total_frames:.2%}) succeeded ({failures['Bad WCS']}/{failures['Bad WCS']/total_frames:.2%} WCS failure, {failures['No match']}/{failures['No match']/total_frames:.2%} no match), {failures['Bad table']}/{failures['Bad table']/total_frames:.2%} catalog problems)")
        zp = np.mean(ephem['V']) - np.mean(mags)
        print(f"ZP={zp:.3f} {np.mean(zps):.3f}")
        if len(nomatch_files) > 0:
            print("Unmatched frames:")
            for frame in nomatch_files:
                print(frame)
        # Make plots
        plot_title = '%s from %s to %s' % (options['target'],
                                           first_frametime.strftime("%Y-%m-%d"),
                                           last_frametime.strftime("%Y-%m-%d"))
        subtitle = 'Sites: ' + header['site_code']
        seeing = fetch_dimm_seeing(header['site_code'], first_frametime)

        plot_timeseries(times, alltimes, mags, magerrs, zps, zp_errs, fwhm, [], {}, seeing, title=plot_title, sub_title=subtitle, datadir=datadir)
