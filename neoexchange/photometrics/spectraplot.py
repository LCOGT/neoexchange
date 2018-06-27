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

#def find_x_units(hdul):


def read_spectra(spectra_file):
    """reads in spectra file
       inputs: <spectra_file>: path and file name to spectra
       outputs: wavelength, flux, flux_error
    """ 
    if spectra_file.endswith('.fits'):   
        hdul = fits.open(spectra_file) #REMINDER: Check for correct file

        data = hdul[0].data
        #find units
        x_min = hdul[0].header['XMIN'] #sometimes "WMIN", sometimes "WMIN"
        x_max = hdul[0].header['XMAX'] #maybe put these two in their own functoin

        flux = np.array(data[0][0]) #putting data into np arrays
        wavelength = np.array([i/len(flux)*(x_max-x_min) + x_min for i in range(len(flux))])
        flux_error = np.array(data[3][0]) #not all formats call this flux error. sometimes it's index 2

    elif spectra_file.endswith('.ascii'):
        data = ascii.read(spectra_file)

        wavelength = np.array([n for n in data['col1']]) #converting tables to np arrays
        flux = np.array([n for n in data['col2']])
        flux_error = np.array([n for n in data['col3']])
              
    else:
        raise OSError("Invalid input file type")

    #eliminate negative error values (Possibly unnecessary)
    flux[np.logical_not(flux >= 0)] = np.nan
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

#def normalize(y, wavelength=5000, units='A')
#do later
#
def plot_spectra(x,y):
    """plots spectra data
       imputs: <x>: wavelength data for x axis
               <y>: flux data for y axis
       outputs:returns ax
    """
    plt.plot(x,y)

if __name__== "__main__":

    path = '/apophis/jchatelain/spectra/'
    spectra = '467309/20180613/ntt467309_U_ftn_20180613_merge_2.0_58283_1_2df_ex.fits'
    #path = '/apophis/tlister/cdbs/calspec/'
    #spectra = 'sun_mod_001.fits'

    sol_ref = 'Solar_analogs/SA98-978/nttLandoltSA98-97_ftn_20180109_merge_2.0_58128_1_2df_ex.fits' 
    
    window = 20 
       
    x,y,y_err = read_spectra(path+spectra) 
    ysmoothed = smooth(y,window)

    xref,yref,y_err_ref = read_spectra(path+sol_ref)
    yrefsmoothed = smooth(yref, window)

    #normy = normalize(y) for later
    #normyref = normalize(yref)

    plot_spectra(x,ysmoothed)
    plot_spectra(xref,yrefsmoothed)
    plt.show()



