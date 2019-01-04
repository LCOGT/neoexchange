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


def make_gif(frames, title=None, sort=True, fr=333):
    """
    takes in list of .fits guide frames and turns them into a moving gif.
    <frames> = list of .fits frame paths
    <title> = [optional] string containing gif title, set to empty string or False for no title
    <sort> = [optional] bool to sort frames by title (Which usually corresponds to date)
    <fr> = frame rate for output gif in ms/frame [default = 333 ms/frame or 3fps]
    output = savefile (path of gif)
    """
    if sort is True:
        fits_files = np.sort(frames)
    else:
        fits_files = frames
    path = os.path.dirname(frames[0]).lstrip(' ')

    # pull header information from first fits file
    with fits.open(fits_files[0], ignore_missing_end=True) as hdul:
        header = hdul['SCI'].header
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
            header = hdul['SCI'].header
            data = hdul['SCI'].data
        # pull Date from Header
        try:
            date_obs = header['DATE-OBS']
        except KeyError:
            date_obs = header['DATE_OBS']
        date = datetime.strptime(date_obs, '%Y-%m-%dT%H:%M:%S.%f')
        # reset plot
        ax = plt.gca()
        ax.clear()
        ax.axis('off')
        wcs = WCS(header)  # get wcs transformation
        z_interval = ZScaleInterval().get_limits(data)  # set z-scale
        # set wcs grid/axes
        ax = plt.gca(projection=wcs)
        dec = ax.coords['dec']
        dec.set_major_formatter('dd:mm')
        dec.set_ticks(exclude_overlapping=True)
        dec.set_ticks_position('br')
        dec.set_ticklabel_position('br')
        dec.set_ticklabel(fontsize=10)
        ra = ax.coords['ra']
        ra.set_major_formatter('hh:mm:ss')
        ra.set_ticks(exclude_overlapping=True)
        ra.set_ticks_position('lb')
        ra.set_ticklabel_position('lb')
        ra.set_ticklabel(fontsize=10)
        ax.coords.grid(color='black', ls='solid', alpha=0.5)
        # finish up plot
        ax.set_title('UTC Date: {} ({} of {})'.format(date.strftime('%Y/%m/%d %X'), n+1, len(fits_files)), pad=10)

        plt.imshow(data, cmap='gray', vmin=z_interval[0], vmax=z_interval[1])
        return ax

    ax1 = update(0)
    plt.tight_layout(pad=4)

    anim = FuncAnimation(fig, update, frames=len(fits_files), blit=False, interval=fr)  # takes in fig, update function, and frame rate set to 3fps

    savefile = os.path.join(path, obj.replace(' ', '_') + '_' + rn + '_guidemovie.gif')
    anim.save(savefile, dpi=90, writer='imagemagick')

    return savefile




