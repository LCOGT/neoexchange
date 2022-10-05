"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2018-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

import sys
import numpy as np
from math import degrees, cos, radians, copysign
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from astropy.io import fits
from astropy.wcs import WCS, FITSFixedWarning
from django.conf import settings
from astropy.wcs._wcs import InvalidTransformError
from astropy.wcs.utils import skycoord_to_pixel
from astropy.coordinates import SkyCoord
from astropy.visualization import ZScaleInterval
from datetime import datetime, timedelta
import calendar
import os
from glob import glob
import argparse
import warnings
import logging

from django.core.files.storage import default_storage

from photometrics.external_codes import unpack_tarball
from photometrics.catalog_subs import unpack_sci_extension
from core.models import Block, Frame, CatalogSources
from astrometrics.ephem_subs import horizons_ephem
from astrometrics.time_subs import timeit
from photometrics.catalog_subs import sanitize_object_name

logger = logging.getLogger(__name__)


def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', time_in=None):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        time_in     - Optional  : if given, will estimate time remaining until completion (Datetime object)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    if time_in is not None:
        now = datetime.now()
        delta_t = now-time_in
        delta_t = delta_t.total_seconds()
        total_time = delta_t/iteration*(float(total)-iteration)
        # print(total_time, delta_t, iteration, float(total))
        if total_time > 90:
            time_left = '| {0:.1f} min remaining |'.format(total_time/60)
        elif total_time > 5400:
            time_left = '| {0:.1f} hrs remaining |'.format(total_time/60/60)
        else:
            time_left = '| {0:.1f} sec remaining |'.format(total_time)
    else:
        time_left = ' '
    print('\r%s |%s| %s%%%s%s' % (prefix, bar, percent, time_left, suffix), end='\r')
    # Print New Line on Complete
    if iteration == total:
        print()


def get_header_info(fits_file):
    with fits.open(fits_file, ignore_missing_end=True) as hdul:
        try:
            header = hdul['SCI'].header
        except KeyError:
            try:
                header = hdul['COMPRESSED_IMAGE'].header
            except KeyError:
                header = hdul[0].header
        # create title
        obj = header['OBJECT']
        try:
            rn = header['REQNUM'].lstrip('0')
        except KeyError:
            rn = 'UNKNOWN'
        try:
            site = header['SITEID'].upper()
        except KeyError:
            site = ' '
        try:
            inst = header['INSTRUME'].upper()
        except KeyError:
            inst = ' '
        if header['OBSTYPE'] in 'GUIDE':
            frame_type = 'guide'
        else:
            frame_type = 'frame'
    return obj, rn, site, inst, frame_type


def make_gif(frames, title=None, sort=True, fr=100, init_fr=1000, progress=True, out_path="", show_reticle=False, center=None, plot_source=False, target_data=None, horizons_comp=False):
    """
    takes in list of .fits guide frames and turns them into a moving gif.
    <frames> = list of .fits frame paths
    <title> = [optional] string containing gif title, set to empty string or False for no title
    <sort> = [optional] bool to sort frames by title (Which usually corresponds to date)
    <fr> = frame rate for output gif in ms/frame [default = 100 ms/frame or 10fps]
    <init_fr> = frame rate for first 5 frames in ms/frame [default = 1000 ms/frame or 1fps]
    <show_reticle> = Bool to determine if reticle present for all guide frames.
    <center> = Display only Central region of frame with this many arcmin/side.
    output = savefile (path of gif)
    """

    if sort is True:
        fits_files = np.sort(frames)
    else:
        fits_files = frames
    path = out_path

    start_frames = 5
    copies = 1
    if init_fr and init_fr > fr and len(fits_files) > start_frames:
        copies = init_fr // fr
        i = 0
        while i < start_frames * copies:
            c = 1
            while c < copies:
                fits_files = np.insert(fits_files, i, fits_files[i])
                i += 1
                c += 1
            i += 1

    # pull out files that exist
    good_fits_files = [f for f in fits_files if os.path.exists(f)]
    base_name_list = [os.path.basename(f) for f in good_fits_files]
    if len(good_fits_files) == 0:
        return "WARNING: COULD NOT FIND FITS FILES"

    fig = plt.figure()
    warnings.simplefilter('ignore', category=FITSFixedWarning)
    frame_query = Frame.objects.filter(filename__in=base_name_list).order_by('midpoint').prefetch_related('catalogsources_set')
    if frame_query:
        frame_obj = frame_query[0]
        end_frame = frame_query.last()
        start = frame_obj.midpoint - timedelta(minutes=5)
        end = end_frame.midpoint + timedelta(minutes=5)
        sitecode = frame_obj.sitecode
        try:
            obj_name = frame_obj.block.body.name
        except AttributeError:
            obj_name = frame_obj.block.calibsource.name
        rn = frame_obj.block.request_number
        if frame_obj.block.obstype == Block.OPT_IMAGING:
            frame_type = 'frame'
        else:
            frame_type = 'guide'
    else:
        with fits.open(good_fits_files[0], ignore_missing_end=True) as hdul:
            try:
                header = hdul['SCI'].header
            except KeyError:
                try:
                    header = hdul['COMPRESSED_IMAGE'].header
                except KeyError:
                    header = hdul[0].header
        obj_name = header['OBJECT']
        rn = header['REQNUM']
        sitecode = header['SITE']
        if header['OBSTYPE'] == 'GUIDE':
            frame_type = 'guide'
        else:
            frame_type = 'frame'

    if horizons_comp:
        # Get predicted JPL position of target in first frame

        try:
            ephem = horizons_ephem(obj_name, start, end, sitecode, ephem_step_size='1m')
            date_array = np.array([calendar.timegm(d.timetuple()) for d in ephem['datetime']])
        except TypeError:
            date_array = []

    time_in = datetime.now()
    x_offset = 0
    y_offset = 0

    def update(n):
        """ this method is required to build FuncAnimation
        <file> = frame currently being iterated
        output: return plot.
        """
        # get data/Header from Fits
        try:
            with fits.open(good_fits_files[n], ignore_missing_end=True) as hdul:
                try:
                    header_n = hdul['SCI'].header
                    data = hdul['SCI'].data
                except KeyError:
                    try:
                        header_n = hdul['COMPRESSED_IMAGE'].header
                        data = hdul['COMPRESSED_IMAGE'].data
                    except KeyError:
                        header_n = hdul[0].header
                        data = hdul[0].data
        except FileNotFoundError:
            if progress:
                logger.warning('Could not find Frame {}'.format(good_fits_files[n]))
            return None

        # pull Date from Header
        try:
            date_obs = header_n['DATE-OBS']
        except KeyError:
            date_obs = header_n['DATE_OBS']
        try:
            date = datetime.strptime(date_obs, '%Y-%m-%dT%H:%M:%S.%f')
        except ValueError:
            date = datetime.strptime(date_obs, '%Y-%m-%dT%H:%M:%S')
        # reset plot
        ax = plt.gca()
        ax.clear()
        ax.axis('off')

        try:
            # set wcs grid/axes
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                wcs = WCS(header_n)  # get wcs transformation
                #ax = plt.gca(projection=wcs)
                # Matplotlib deprecated above in 3.4
                ax = plt.subplot(projection=wcs)
            dec = ax.coords['dec']
            # Disabling Automatic Labelling to stop 'pos.eq.dec' labels showing up
            dec.set_auto_axislabel(False)
            dec.set_major_formatter('dd:mm')
            dec.set_ticks_position('br')
            dec.set_ticklabel_position('br')
            dec.set_ticklabel(fontsize=10, exclude_overlapping=True)
            ra = ax.coords['ra']
            ra.set_auto_axislabel(False)
            ra.set_major_formatter('hh:mm:ss')
            ra.set_ticks_position('lb')
            ra.set_ticklabel_position('lb')
            ra.set_ticklabel(fontsize=10, exclude_overlapping=True)
            ax.coords.grid(color='black', ls='solid', alpha=0.5)
        except InvalidTransformError:
            pass
        # finish up plot
        current_count = len(np.unique(good_fits_files[:n + 1]))

        if title is None:
            sup_title = f'REQ# {header_n["REQNUM"]} -- {header_n["OBJECT"]} at {header_n["SITEID"].upper()} ({header_n["INSTRUME"]}) -- Filter: {header_n["FILTER"]}'
        else:
            sup_title = title
        ax.set_title(sup_title + '\n' + f'UT Date: {date.strftime("%x %X")} Frame:{header_n["FRAMENUM"]:04d} '
                                        f'({current_count} of'
                                        f' {int(len(good_fits_files) - (copies - 1) * start_frames)})')

        # Set frame to be center of chip in arcmin
        shape = data.shape
        x_frac = 0
        y_frac = 0
        if center is not None:
            width = (center * 60) / header_n['PIXSCALE']
            y_frac = np.max(int((shape[0] - width) / 2), 0)
            x_frac = np.max(int((shape[1] - width) / 2), 0)

            # set data ranges
            data_x_range = [x_frac, -(x_frac+1)]
            data_y_range = [y_frac, -(y_frac+1)]
            if target_data:
                nonlocal x_offset
                nonlocal y_offset
                td = target_data[n]
                coord = SkyCoord(td['ra'], td['dec'], unit="rad")
                x_pix, y_pix = skycoord_to_pixel(coord, wcs)
                x_offset = int(x_pix - header_n['CRPIX1'])
                y_offset = int(y_pix - header_n['CRPIX2'])
                if abs(x_offset) > x_frac:
                    x_offset = int(copysign(x_frac, x_offset))
                if abs(y_offset) > y_frac:
                    y_offset = int(copysign(y_frac, y_offset))
                data_x_range = [x + x_offset for x in data_x_range]
                data_y_range = [y + y_offset for y in data_y_range]
                x_frac += x_offset
                y_frac += y_offset
            data = data[data_y_range[0]:data_y_range[1], data_x_range[0]:data_x_range[1]]
            # Set new coordinates for Reference Pixel w/in smaller window
            header_n['CRPIX1'] -= x_frac
            header_n['CRPIX2'] -= y_frac

        z_interval = ZScaleInterval().get_limits(data)  # set z-scale: responsible for vast majority of compute time
        plt.imshow(data, cmap='gray', vmin=z_interval[0], vmax=z_interval[1])

        # If first few frames, add 5" and 15" reticle
        if current_count < 6 and fr != init_fr or show_reticle:
            if plot_source and (data.shape[1] > header_n['CRPIX1'] > 0) and (data.shape[0] > header_n['CRPIX2'] > 0):
                plt.plot([header_n['CRPIX1']], [header_n['CRPIX2']], color='red', marker='+', linestyle=' ', label="Frame_Center")
            else:
                circle_5arcsec = plt.Circle((header_n['CRPIX1'], header_n['CRPIX2']), 5/header_n['PIXSCALE'], fill=False, color='limegreen', linewidth=1.5)
                circle_15arcsec = plt.Circle((header_n['CRPIX1'], header_n['CRPIX2']), 15/header_n['PIXSCALE'], fill=False, color='lime', linewidth=1.5)
                ax.add_artist(circle_5arcsec)
                ax.add_artist(circle_15arcsec)

        # add sources
        if plot_source:
            try:
                frame_obj = Frame.objects.get(filename=os.path.basename(good_fits_files[n]))
                sources = CatalogSources.objects.filter(frame=frame_obj, obs_y__range=(y_frac, shape[0] - y_frac + 2 * y_offset), obs_x__range=(x_frac, shape[1] - x_frac + 2 * x_offset))
                for source in sources:
                    circle_source = plt.Circle((source.obs_x - x_frac, source.obs_y - y_frac), 3/header_n['PIXSCALE'], fill=False, color='red', linewidth=1, alpha=.5)
                    ax.add_artist(circle_source)
            except Frame.DoesNotExist:
                pass

        # Highlight best target and search box
        x_pix = header_n['CRPIX1']
        y_pix = header_n['CRPIX2']
        if target_data:
            td = target_data[n]
            target_source = td['best_source']
            if target_source:
                target_circle = plt.Circle((target_source.obs_x - x_frac, target_source.obs_y - y_frac), 3/header_n['PIXSCALE'], fill=False, color='limegreen', linewidth=1)
                ax.add_artist(target_circle)
            bw = td['bw']
            bw /= header_n['PIXSCALE']
            coord = SkyCoord(td['ra'], td['dec'], unit="rad")
            # if target_source:
            #     print(coord.separation(SkyCoord(target_source.obs_ra, target_source.obs_dec, unit="deg")).arcsec)
            x_pix, y_pix = skycoord_to_pixel(coord, wcs)
            box_width = plt.Rectangle((x_pix-bw-x_frac, y_pix-bw-y_frac), width=bw*2, height=bw*2, fill=False, color='yellow', linewidth=1, alpha=.5)
            ax.add_artist(box_width)

        # show the position of the JPL Horizons prediction relative to CRPIX if no target data.
        if horizons_comp and date_array.any():
            jpl_ra = np.interp(calendar.timegm(date.timetuple()), date_array, ephem['RA'])
            jpl_dec = np.interp(calendar.timegm(date.timetuple()), date_array, ephem['DEC'])
            jpl_coord = SkyCoord(jpl_ra, jpl_dec, unit="deg")
            jpl_x_pix, jpl_y_pix = skycoord_to_pixel(jpl_coord, wcs)
            if target_data and jpl_coord.separation(coord).arcsec > 3:
                plt.plot([x_pix, jpl_x_pix], [y_pix, jpl_y_pix], color='lightblue', linestyle='-', linewidth=1, alpha=.5)
                plt.plot([jpl_x_pix], [jpl_y_pix], color='blue', marker='x', linestyle=' ', label="JPL Prediction")
            elif not target_data:
                plt.plot([jpl_x_pix], [jpl_y_pix], color='blue', marker='x', linestyle=' ', label="JPL Prediction")

        if progress:
            print_progress_bar(n+1, len(good_fits_files), prefix='Creating Gif: Frame {}'.format(current_count), time_in=time_in)
        return ax

    ax1 = update(0)
    plt.tight_layout(pad=4)

    # takes in fig, update function, and frame rate set to fr
    anim = FuncAnimation(fig, update, frames=len(good_fits_files), blit=False, interval=fr)

    filename = os.path.join(path, sanitize_object_name(obj_name) + '_' + rn + '_{}movie.gif'.format(frame_type))
    anim.save(filename, dpi=90, writer='imagemagick')

    plt.close('all')
    # Save to default location because Matplotlib wants a string filename not File object

    return filename


def make_movie(date_obs, obj, req, base_dir, out_path, prop, tarfile=None):
    """Make gif of FLOYDS Guide Frames given the following:
    <date_obs> -- Day of Observation (i.e. '20180910')
    <obj> -- object name w/ spaces replaced by underscores (i.e. '144332' or '2018_EB1')
    <req> -- Request number of the observation
    <base_dir> -- Directory of data. This will be the DATA_ROOT/date_obs/
    <prop> -- Proposal ID
    NOTE: Can take a while to load if building new gif with many frames.
    """

    path = os.path.join(base_dir, obj + '_' + req)
    logger.info('BODY: {}, DATE: {}, REQNUM: {}, PROP: {}'.format(obj, date_obs, req, prop))
    logger.debug('DIR: {}'.format(path))  # where it thinks an unpacked tar is at

    filename = glob(os.path.join(path, '*2df_ex.fits'))  # checking if unpacked
    frames = []
    if not filename:
        unpack_path = os.path.join(base_dir, obj+'_'+req)
        if tarfile:
            logger.info("Unpacking tarfile")
            spec_files = unpack_tarball(os.path.join(base_dir, tarfile), unpack_path)  # unpacks tarball
            filename = spec_files[0]
        else:
            tar_files = glob(os.path.join(base_dir, prop+"*"+req+"*.tar.gz"))  # if file not found, looks for tarball
            if tar_files:
                tar_path = tar_files[0]
                logger.info("Unpacking 1st tar")
                spec_files = unpack_tarball(tar_path, unpack_path)  # unpacks tarball
                filename = spec_files[0]
            else:
                logger.error("Could not find tarball for request: %s" % req)
                return None
    if filename:  # If first order tarball is unpacked
        movie_dir = os.path.join(path, "Guide_frames")
        if not os.path.exists(movie_dir):  # unpack 2nd tarball
            tarintar = glob(os.path.join(path, "*.tar"))
            if tarintar:
                guide_files = unpack_tarball(tarintar[0], movie_dir)  # unpacks tar
                logger.info("Unpacking tar in tar")
                for gf in guide_files:
                    if '.fits.fz' in gf:
                        unpack_sci_extension(gf)
            else:
                logger.error("Could not find Guide Frames or Guide Frame tarball for request: %s" % req)
                return None
        frames = glob(os.path.join(movie_dir, "*.fits"))
    else:
        logger.error("Could not find spectrum data or tarball for request: %s" % req)
        return None
    if frames is not None and len(frames) > 0:
        logger.debug("#Frames = {}".format(len(frames)))
        logger.info("Making Movie...")
        movie_file = make_gif(frames, out_path=out_path, progress=False)
        return movie_file
    else:
        logger.error("There must be at least 1 frame to make guide movie.")
        return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="Path to directory containing .fits or .fits.fz files", type=str)
    parser.add_argument("--fr", help="Frame rate in ms/frame (Defaults to 100 ms/frame or 10 frames/second", default=100, type=float)
    parser.add_argument("--ir", help="Frame rate in ms/frame for first 5 frames (Defaults to 1000 ms/frame or 1 frames/second", default=1000, type=float)
    parser.add_argument("--tr", help="Add target circle at crpix values?", default=False, action="store_true")
    parser.add_argument("--C", help="Only include Center Snapshot (Value= new FOV in in Arcmin)", default=None, type=float)
    args = parser.parse_args()
    path = args.path
    fr = args.fr
    ir = args.ir
    tr = args.tr
    center = args.C
    logger.debug("Base Framerate: {}".format(fr))
    if path[-1] != '/':
        path += '/'
    files = np.sort(glob(path+'*.fits.fz'))
    if len(files) < 1:
        files = np.sort(glob(path+'*.fits'))
    if len(files) >= 1:
        gif_file = make_gif(files, fr=fr, init_fr=ir, show_reticle=tr, out_path=path, center=center, progress=True)
        logger.info("New gif created: {}".format(gif_file))
    else:
        logger.info("No files found.")
