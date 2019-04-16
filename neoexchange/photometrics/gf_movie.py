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
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from astropy.io import fits
from astropy.wcs import WCS
from astropy.visualization import ZScaleInterval
from datetime import datetime
import os
from glob import glob
import argparse


def make_gif(frames, title=None, sort=True, fr=100, init_fr=1000):
    """
    takes in list of .fits guide frames and turns them into a moving gif.
    <frames> = list of .fits frame paths
    <title> = [optional] string containing gif title, set to empty string or False for no title
    <sort> = [optional] bool to sort frames by title (Which usually corresponds to date)
    <fr> = frame rate for output gif in ms/frame [default = 100 ms/frame or 10fps]
    <init_fr> = frame rate for first 5 frames in ms/frame [default = 1000 ms/frame or 1fps]
    output = savefile (path of gif)
    """
    if sort is True:
        fits_files = np.sort(frames)
    else:
        fits_files = frames
    path = os.path.dirname(frames[0]).lstrip(' ')

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

    # pull header information from first fits file
    with fits.open(fits_files[0], ignore_missing_end=True) as hdul:
        try:
            header = hdul['SCI'].header
        except KeyError:
            header = hdul['COMPRESSED_IMAGE'].header
        # create title
        obj = header['OBJECT']
        rn = header['REQNUM'].lstrip('0')
        site = header['SITEID'].upper()
        inst = header['INSTRUME'].upper()

    if title is None:
        title = 'Request Number {} -- {} at {} ({})'.format(rn, obj, site, inst)

    fig = plt.figure()
    if title:
        fig.suptitle(title)

    def update(n):
        """ this method is required to build FuncAnimation
        <file> = frame currently being iterated
        output: return plot.
        """
        # get data/Header from Fits
        with fits.open(fits_files[n], ignore_missing_end=True) as hdul:
            try:
                header_n = hdul['SCI'].header
                data = hdul['SCI'].data
            except KeyError:
                header_n = hdul['COMPRESSED_IMAGE'].header
                data = hdul['COMPRESSED_IMAGE'].data
        # pull Date from Header
        try:
            date_obs = header_n['DATE-OBS']
        except KeyError:
            date_obs = header_n['DATE_OBS']
        date = datetime.strptime(date_obs, '%Y-%m-%dT%H:%M:%S.%f')
        # reset plot
        ax = plt.gca()
        ax.clear()
        ax.axis('off')
        wcs = WCS(header_n)  # get wcs transformation
        z_interval = ZScaleInterval().get_limits(data)  # set z-scale
        # set wcs grid/axes
        ax = plt.gca(projection=wcs)
        dec = ax.coords['dec']
        dec.set_major_formatter('dd:mm')
        dec.set_ticks_position('br')
        dec.set_ticklabel_position('br')
        dec.set_ticklabel(fontsize=10, exclude_overlapping=True)
        ra = ax.coords['ra']
        ra.set_major_formatter('hh:mm:ss')
        ra.set_ticks_position('lb')
        ra.set_ticklabel_position('lb')
        ra.set_ticklabel(fontsize=10, exclude_overlapping=True)
        ax.coords.grid(color='black', ls='solid', alpha=0.5)
        # finish up plot
        current_count = len(np.unique(fits_files[:n+1]))
        ax.set_title('UT Date: {} ({} of {})'.format(date.strftime('%x %X'), current_count, int(len(fits_files)-(copies-1)*start_frames)), pad=10)

        plt.imshow(data, cmap='gray', vmin=z_interval[0], vmax=z_interval[1])

        # If first few frames, add 5" and 15" reticle
        if current_count < 6:
            circle_5arcsec = plt.Circle((header_n['CRPIX1'], header_n['CRPIX2']), 5/header_n['PIXSCALE'], fill=False, color='limegreen', linewidth=1.5)
            circle_15arcsec = plt.Circle((header_n['CRPIX1'], header_n['CRPIX2']), 15/header_n['PIXSCALE'], fill=False, color='lime', linewidth=1.5)
            ax.add_artist(circle_5arcsec)
            ax.add_artist(circle_15arcsec)
        return ax

    ax1 = update(0)
    plt.tight_layout(pad=4)

    # takes in fig, update function, and frame rate set to fr
    anim = FuncAnimation(fig, update, frames=len(fits_files), blit=False, interval=fr)

    savefile = os.path.join(path, obj.replace(' ', '_') + '_' + rn + '_guidemovie.gif')
    anim.save(savefile, dpi=90, writer='imagemagick')

    return savefile


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="Path to directory containing .fits or .fits.fz files", type=str)
    parser.add_argument("--fr", help="Frame rate in ms/frame (Defaults to 100 ms/frame or 10 frames/second", default=100, type=float)
    parser.add_argument("--ir", help="Frame rate in ms/frame for first 5 frames (Defaults to 1000 ms/frame or 1 frames/second", default=1000, type=float)
    args = parser.parse_args()
    path = args.path
    fr = args.fr
    ir = args.ir
    print(fr)
    if path[-1] != '/':
        path += '/'
    files = np.sort(glob(path+'*.fits.fz'))
    if len(files) < 1:
        files = np.sort(glob(path+'*.fits'))
    if len(files) >= 1:
        gif_file = make_gif(files, fr=fr, init_fr=ir)
        print("New gif created: {}".format(gif_file))
    else:
        print("No files found.")

