"""
convert 1D fits spectra into a readable plot
Written by Adam Tedeschi
Date: 6/25/2018
for NeoExchange
"""

from astropy.io import fits
from astropy.convolution import convolve, Box1DKernel
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

np.set_printoptions(threshold=np.inf)

def read_spectra(spectra_file):
    """reads in spectra file
       inputs: <spectra_file>: path and file name to spectra
       outputs: wavelength, flux, flux_error
    """    
    hdul = fits.open(spectra_file) #Check for correct file

    data = hdul[0].data

    x_min = hdul[0].header['XMIN']
    x_max = hdul[0].header['XMAX']

    flux = np.array(data[0][0])
    wavelength= np.array([i/len(flux)*(x_max-x_min) + x_min for i in range(len(flux))])
    flux_error = np.array(data[3][0])
    return wavelength, flux, flux_error

def smooth(ydata, window=20):
    """uses boxcar averaging to smooth flux data
       inputs: <ydata>: raw flux data
               [window]: size of smoothing window (default = 20)
       outputs: smoothed flux data
    """
    return convolve(ydata, Box1DKernel(window)) #boxcar average data

if __name__== "__main__":
    path = '/apophis/jchatelain/spectra/'
    spectra = '16/ntt16_ftn_20180606_merge_2.0_58276_1_2df_ex.fits'

    x,y,y_err = read_spectra(path+spectra)

    ysmoothed = smooth(y,20)

    plt.plot(x,y,'b-')
    plt.plot(x,ysmoothed,'r-')

    plt.show()




