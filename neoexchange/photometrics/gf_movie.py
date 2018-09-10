"""
Creates a guide frame movie gif when given a series of guide frames
Author: Adam Tedeschi
Date: 8/10/2018
for NeoExchange
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

    if title is None:
        # pull header information from first fits file
        with fits.open(fits_files[0]) as hdul:
            header = hdul['SCI'].header
            # create title
            obj = header['OBJECT']
            tn = header['TRACKNUM'].lstrip('0')
            site = header['SITEID'].upper()
            inst = header['INSTRUME'].upper()
            title = 'Tracking Number {} -- {} at {} ({})'.format(tn, obj, site, inst)

    fig = plt.figure()
    if title:
        fig.suptitle(title)

    def update(n):
        """ this method is required to build FuncAnimation
        <file> = frame currently being iterated
        output: return plot.
        """
        # get data/Header from Fits
        with fits.open(fits_files[n]) as hdul:
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
        ax.set_title('UT Date: {} ({} of {})'.format(date.strftime('%x %X'), n+1, len(fits_files)), pad=10)

        plt.imshow(data, cmap='gray', vmin=z_interval[0], vmax=z_interval[1])
        return ax

    ax1 = update(0)
    plt.tight_layout(pad=4)

    anim = FuncAnimation(fig, update, frames=len(fits_files), blit=False, interval=fr)  # takes in fig, update function, and frame rate set to 3fps

    savefile = os.path.join(path, 'guidemovie.gif')
    anim.save(savefile, dpi=90, writer='imagemagick')

    return savefile




