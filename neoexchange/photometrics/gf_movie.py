"""Creates a guide frame movie gif when given a series of guide frames"""
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from astropy.io import fits
from astropy.wcs import WCS
from astropy.visualization import ZScaleInterval
from astropy import units as u
from glob import glob
import os

def make_gif(frames):
    files = np.sort(frames)
    dir = os.path.dirname(frames[0])

    hdu = fits.open(files[0])[0]
    if not hdu.data:
        hdu = fits.open(files[0])[1]

    data = hdu.data
    header = hdu.header

    obj = header['OBJECT']
    tn = header['TRACKNUM'].lstrip('0')
    try:
        date = header['DATE-OBS'][:-4]
    except KeyError:
        date = header['DATE_OBS'][:-4]
    if header['SITEID'] == 'ogg':
        site = 'FTN'
    else:
        site = 'FTS'
    #wcs = WCS(header)
    interval = ZScaleInterval().get_limits(data)

    fig = plt.figure()
    #fig.add_subplot(111,projection=wcs)
    fig.suptitle('Observation '+tn+' for '+obj+' at '+site)
    image = plt.imshow(fits.getdata(files[0]),cmap='gray',vmin=interval[0],vmax=interval[1])
    ax = plt.gca()
    ax.set_title('Date: '+date)
    ax.set_xlabel('RA Dec: '+header['RA']+ ' '+header['DEC'])
    plt.tick_params(
    axis='both',
    which='both',
    bottom=False,
    left=False,
    labelbottom=False,
    labelleft=False)

    anim = FuncAnimation(fig,update,frames=np.arange(len(files)),blit=True,interval=333)

    savefile = dir+'guidemovie.gif'
    anim.save(savefile, dpi=80, writer='imagemagick')

    return savefile

def update(i):

    data = fits.getdata(files[i])
    header = fits.open(files[i])[0].header
    try:
        date = header['DATE-OBS'][:-4]
    except KeyError:
        date = header['DATE_OBS'][:-4]
    #wcs = WCS(header)
    interval = ZScaleInterval().get_limits(data)
    ax = plt.gca()
    #lon = ax.coords['ra']

    return plt.imshow(data,cmap='gray',vmin=interval[0],vmax=interval[1]),ax.set_title('Date: '+date),ax.set_xlabel('RA Dec: '+header['RA']+ ' '+header['DEC'])

if __name__ == '__main__':

    dir = '/home/atedeschi/Asteroids/20180731/398188_0001604640/Guide_Frames/'
    files = np.sort(glob(dir+'*.fits'))
    hdu = fits.open(files[0])[0]
    data = hdu.data
    header = hdu.header

    minind = np.unravel_index(np.argmin(data, axis=None), data.shape)
    min = data[minind]

    obj = header['OBJECT']
    tn = header['TRACKNUM'].lstrip('0')
    try:
        date = header['DATE-OBS'][:-4]
    except KeyError:
        date = header['DATE_OBS'][:-4]
    if header['SITEID'] == 'ogg':
        site = 'FTN'
    else:
        site = 'FTS'
    #wcs = WCS(header)
    interval = ZScaleInterval().get_limits(data)

    fig = plt.figure()
    #fig.add_subplot(111,projection=wcs)
    fig.suptitle('Observation '+tn+' for '+obj+' at '+site)
    image = plt.imshow(fits.getdata(files[0]),cmap='gray',vmin=interval[0],vmax=interval[1])
    ax = plt.gca()
    ax.set_title('Date: '+date)
    ax.set_xlabel('RA Dec: '+header['RA']+ ' '+header['DEC'])
    plt.tick_params(
    axis='both',
    which='both',
    bottom=False,
    left=False,
    labelbottom=False,
    labelleft=False)

    # lon.set_major_formatter('hh:mm:ss')
    # lat.set_major_formatter('dd:mm:ss')
    # lon.set_ticks_position('l')
    # lon.set_ticklabel_position('l')
    # lat.set_ticks_position('b')
    # lat.set_ticklabel_position('b')
    # lon.set_axislabel('Dec',rotation=90) #I know it's reversed. It works though.
    # lat.set_axislabel('RA')
    # lon.set_ticks(number = 6)
    # lat.set_ticks(number = 6)
    # lon.set_ticklabel(fontsize=10,rotation=90)
    # lat.set_ticklabel(fontsize=10)
    # ax.coords.grid(color='w',alpha =.5)

    anim = FuncAnimation(fig,update,frames=np.arange(len(files)),blit=True,interval=333)

    #plt.show()

    savefile = dir+'guidemovie.gif'
    anim.save(savefile, dpi=80, writer='imagemagick')
