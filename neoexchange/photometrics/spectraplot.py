"""
convert 1D fits spectra into a readable plot
Written by Adam Tedeschi
Date: 6/25/2018
for NeoExchange
"""

from astropy.io import fits
from astropy.io import ascii
from astropy.convolution import convolve, Box1DKernel
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

#np.set_printoptions(threshold=np.inf)

def read_spectra(spectra_file):
    """reads in spectra file
       inputs: <spectra_file>: path and file name to spectra
       outputs: wavelength, flux, flux_error
    """ 
    if spectra_file.endswith('.fits'):   
        hdul = fits.open(spectra_file) #REMINDER: Check for correct file

        data = hdul[0].data

        x_min = hdul[0].header['XMIN']
        x_max = hdul[0].header['XMAX']

        flux = np.array(data[0][0]) #putting data into np arrays
        wavelength = np.array([i/len(flux)*(x_max-x_min) + x_min for i in range(len(flux))])
        flux_error = np.array(data[3][0])

    if spectra_file.endswith('.ascii'):
        data = ascii.read(spectra_file)

        wavelength = np.array([n for n in data['col1']]) #converting tables to np arrays
        flux = np.array([n for n in data['col2']])
        flux_error = np.array([n for n in data['col3']])
              
    else:
        raise OSError(erno.EIO,"Invalid input file type")

    flux[np.logical_not(flux >= 0)] = np.nan #eliminate negative error values
    flux_error[np.logical_not(flux_error >= 0)] = np.nan
    
    return wavelength, flux, flux_error
        

def smooth(ydata, window=20):
    """uses boxcar averaging to smooth flux data
       inputs: <ydata>: raw flux data
               [window]: size of smoothing window (default = 20)
       outputs: smoothed flux data
    """

    if len(ydata) < window:
        raise ValueError("Input vector needs to be bigger than window size.")

    if window < 3:
        return ydata

    if window % 2 != 0:
        window += 1

    return convolve(ydata, Box1DKernel(window)) #boxcar average data

def plot_spectra(x,y):
    """plots spectra data
       imputs: <x>: wavelength data for x axis
               <y>: flux data for y axis
       outputs:returns ax (FOR LATER)
    """
    plt.plot(x,y,'b-')
    plt.show()
    

if __name__== "__main__":
    #path = '/apophis/jchatelain/spectra/'
    #spectra = '16/ntt16_ftn_20180606_merge_2.0_58276_1_2df_ex.fits'
    path = '/apophis/tlister/cdbs/calspec/'
    spectra = 'eros_visnir_reference_to1um.ascii'
    window = 2 
       
    x,y,y_err = read_spectra(path+spectra)  

    ysmoothed = smooth(y,window)

    plot_spectra(x,ysmoothed)



