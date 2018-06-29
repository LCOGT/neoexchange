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
import collections

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
        print("WARNING: Could not parse wavelength units from file. Assuming Angstoms")
        x_units = u.AA 
               
    return x_units
    
def get_y_units(info):
    flux_id = ["erg", "ERG", "FLAM"] #can add more later
    #I know erg isn't the full unit, but it's a good indicator.
    norm_id = ["NORM", "REFLECTANCE"]
    if isinstance(info, collections.OrderedDict): #From .ascii
        col_head = list(info.values())[0][0]
        if any(unit_id in col_head.upper() for unit_id in flux_id):
            y_unit = u.erg/(u.cm**2)/u.s/u.AA
            print(y_units)
        elif any(unit_id in col_head for unit_id in norm_id):
            y_units = (1*u.m/u.m).unit.decompose()
            print(y_units, "(normalized)")
        else:
            print("WARNING: Could not parse flux units from file. Assuming erg/cm^2/s/A")
            y_units = u.erg/(u.cm**2)/u.s/u.AA

    elif isinstance(info, fits.header.Header):  #from .fits
        possible_keys = ['BUNIT','TUNIT2'] #maybe add more later
        for keys in info.keys():
              if any(unit_key in keys for unit_key in possible_keys):  
                    if any(unit_id in keys for unit_id in flux_id):
                        if any("10^20" in keys for key in unit_keys):
                            y_units = u.erg/(u.cm**2)/u.s/u.AA*10**20
                            print(y_units)
                        else:
                            y_units = u.erg/(u.cm**2)/u.s/u.AA
                            print(y_units)
                    elif any(unit_id in keys for unit_id in norm_id):
                        y_units = (1*u.m/u.m).unit.decompose()
                        print(y_units, "(normalized)")
        #TEMPORARY
        print("WARNING: Could not parse flux units from file. Assuming erg/cm^2/s/A")
        y_units = u.erg/(u.cm**2)/u.s/u.AA


    return y_units

def read_spectra(spectra_file):
    """reads in spectra file (currently only works with LCO standards)
       inputs: <spectra_file>: path and file name to spectra
       outputs: wavelength (Quantity type), flux, flux_error
    """ 
    if spectra_file.endswith('.fits'):   
        hdul = fits.open(spectra_file) #read in data

    #fits standard 1:
        if hdul[0].data is not None:
            data = hdul[0].data
            hdr = hdul[0].header   
            y_data = data.flatten()[:max(data.shape)]
            w = WCS(hdr, naxis=1,relax=False,fix=False)
            x_data = w.wcs_pix2world(np.arange(len(y_data)),0)[0]
            
            try:
                flux_error = np.array(data[3][0]) 
            except IndexError:
                print("WARNING: Could not parse error data")
                flux_error = np.zeros(len(x_data))
    #fits standard 2:    
        elif hdul[1].data is not None:
            data = hdul[1].data
            hdr = hdul[1].header
            x_data = np.array([])
            y_data = np.array([])           
            for n in data: #SUPER INEFFICIENT, CHANGE!
                x_data = np.append(x_data,n[0])
                y_data = np.append(y_data,n[1])
            flux_error = np.zeros(len(x_data))
        else:
            raise ImportError("Could not read data from .fits file")

        x_units = get_x_units(x_data)
        y_units = get_y_units(hdr)

    elif spectra_file.endswith('.ascii'):
        data = ascii.read(spectra_file) #read in data
        #print(data.meta)
        #assuming 3 columns: wavelength, flux/reflectance, error
        x_data = data['col1'] #converting tables to ndarrays
        y_data = data['col2']
        flux_error = data['col3']
        x_units = get_x_units(x_data)
        y_units = get_y_units(data.meta)
              
    else:
        raise ImportError("Invalid input file type")

    #eliminate negative error values (Possibly unnecessary)
    y_data[np.logical_not(y_data >= 0)] = np.nan
    flux_error[np.logical_not(flux_error >= 0)] = np.nan
    
    wavelength = (x_data*x_units).to(u.AA) 
    #convert all wavelengths to Angstroms because it's easy to deal with that way
    flux = y_data*y_units    

    return wavelength, flux, flux_error, x_units, y_units
        

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

def normalize(x,y,yerr,wavelength=5500*u.AA):
    """normalizes flux data with a specific wavelength flux value
       inputs: <x>: wavelenth data (Quantity type)
               <y>: flux data (Quantity type)
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
    #spectra = '467309/20180613/ntt467309_U_ftn_20180613_merge_2.0_58283_1_2df_ex.fits'
    #spectra = 'calspec/eros_visnir_reference_to1um.ascii'
    spectra = 'calspec/sun_mod_001.fits'

    #sol_ref = 'Solar_analogs/HD209847/nttHD209847_ftn_20180625_merge_2.0_58295_2_2df_ex.fits'
    sol_ref =  'solar_standard_V2.fits'

    window = 20 # 2 for eros ascii file. 20 for most others
    x,y,yerr,x_units,y_units = read_spectra(path+spectra) 
    ysmoothed = smooth(y,window)#[window/2:-window/2]

    #Smoothing may cause artifacts at data ends.
    
    window_ref = 20
    x_ref,y_ref,yerr_ref,x_ref_units,y_ref_units = read_spectra(path+sol_ref)
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
    



