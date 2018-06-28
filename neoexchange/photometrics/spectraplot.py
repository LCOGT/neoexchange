"""
convert 1D fits spectra into a readable plot
Written by Adam Tedeschi
Date: 6/25/2018
for NeoExchange
"""

from astropy.io import fits, ascii
from astropy.convolution import convolve, Box1DKernel #Gaussian1DKernel
from astropy.wcs import WCS
from astropy import units as u
import matplotlib.pyplot as plt
#import matplotlib.ticker as ticker
import numpy as np

#np.set_printoptions(threshold=np.inf)

def get_x_units(x_data):
    """finds wavelength units from x_data
       inputs: <xdata>: unitless wavelength data
       outputs: x_units
    """ 
    #xdata should be ndarray type. Will try error handling for it later
    x_min = np.amin(x_data)

    #assuming visible to NIR range (~3000-10000A)
    if x_min >1000:
        x_units = u.AA #(Angstroms)
    elif 100 < x_min < 1000:
        x_units = u.PrefixUnit(nm)
    elif .1 < x_min < 1:
        x_units = u.micron
    else:
        print("Warning: Could not parse wavelength units from file. Assuming Angstoms")
        x_units = u.AA 
               
    return x_units
    
def read_spectra(spectra_file):
    """reads in spectra file (currently only works with LCO standards)
       inputs: <spectra_file>: path and file name to spectra
       outputs: wavelength (Quantity type), flux, flux_error
    """ 
    if spectra_file.endswith('.fits'):   
        hdul = fits.open(spectra_file) #read in data

        #print(hdul.info())
        data = hdul[0].data
        hdr = hdul[0].header

        flux = data.flatten()[:max(data.shape)] 
        w = WCS(hdr, naxis=1,relax=False,fix=False)
        x_data = w.wcs_pix2world(np.arange(len(flux)),0)[0]
        x_units = get_x_units(x_data)
        
        try:
            flux_error = np.array(data[3][0]) 
        except IndexError:
            print("Could not parse error data")
            flux_error = np.zeros()

    elif spectra_file.endswith('.ascii'):
        data = ascii.read(spectra_file) #read in data
        #assuming 3 columns: wavelength, flux/reflectance, error
        x_data = data['col1'] #converting tables to ndarrays
        flux = data['col2']
        flux_error = data['col3']
        x_units = get_x_units(x_data)
              
    else:
        raise OSError("Invalid input file type")

    #eliminate negative error values (Possibly unnecessary)
    flux[np.logical_not(flux >= 0)] = np.nan
    flux_error[np.logical_not(flux_error >= 0)] = np.nan
    
    wavelength = (x_data*x_units).to(u.AA) #convert all wavelengths to Angstroms
    return wavelength, flux, flux_error,x_units
        

def smooth(ydata, window=20):
    """uses boxcar averaging to smooth flux data
       inputs: <ydata>: raw flux data
               [window]: size of smoothing window (default = 20)
       outputs: smoothed flux data
    """

    if len(ydata) < window:
        raise ValueError("Input vector must be bigger than window size.")

    if window < 3:
        return ydata

    #if window % 2 != 0: I believe Box 1D kernel handles this already
    #    window += 1

    return convolve(ydata, Box1DKernel(window)) #boxcar average data

def normalize(x,y,yerr,wavelength=5000*u.AA):
    """normalizes flux data with a specific wavelength flux value
       inputs: <x>: wavelenth data (Quantity type)
               <y>: flux data
               <yerr>: 
               [wavelength]: target wavelength to normalize at (Quantity type)
       outputs: normalized flux data
    """
    normval = y[np.abs(x-wavelength).argmin()] #uses closest data point to target wavelength
    return y/normval,yerr/normval

def plot_spectra(x,y):
    """plots spectra data
       imputs: <x>: wavelength data for x axis
               <y>: flux data for y axis
       outputs:returns ax DO LATER
    """
    plt.plot(x,y)

if __name__== "__main__":

    path = '/home/atedeschi/test_spectra/' #will make more general file passing later
    spectra = '467309/20180613/ntt467309_U_ftn_20180613_merge_2.0_58283_1_2df_ex.fits'
    #spectra = 'calspec/eros_visnir_reference_to1um.ascii'
    #spectra = 'calspec/sun_mod_001.fits'

    sol_ref = 'Solar_analogs/HD209847/nttHD209847_ftn_20180625_merge_2.0_58295_2_2df_ex.fits'
    
    window = 20 # 2 for eros ascii file. 20 for most others
    x,y,yerr,x_units = read_spectra(path+spectra) 
    ysmoothed = smooth(y,window)

    #Smoothing may cause artifacts at data ends.
    #consider only plotting x[window:-window] and ysmoothed[window:-window]
    
    window_ref = 20
    x_ref,y_ref,yerr_ref,x_ref_units = read_spectra(path+sol_ref)
    y_refsmoothed = smooth(y_ref, window_ref)
    
    #print(x.shape, y.shape, x_ref.shape, y_ref.shape, ysmoothed.shape, y_refsmoothed.shape)

    normy, normyerr = normalize(x,ysmoothed,yerr) #normalizing data
    normy_ref,normerr_ref = normalize(x_ref,y_refsmoothed,yerr_ref)
    
    #print(yerr)
    #print(normyerr)
    
    #plotting data
    plot_spectra(x,normy)
    plot_spectra(x_ref,normy_ref)
    plt.show()
    



