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
import collections,warnings

#np.set_printoptions(threshold=np.inf)

def get_x_units(x_data):
    """finds wavelength units from x_data
       inputs: <xdata>: unitless wavelength data
       outputs: x_units
    """
    #xdata should be ndarray type. Will try error handling for it later
    x_min = np.amin(x_data)

    #assuming visible to NIR range (~3000-10000A)
    if x_min >800:
        x_units = u.AA #(Angstroms)
    elif 100 < x_min < 800:
        x_units = u.nm
    elif .1 < x_min < 1:
        x_units = u.micron
    else:
        print("WARNING: Could not parse wavelength units from file. Assuming Angstoms")
        x_units = u.AA
    print("x_units: ",x_units)

    return x_units

def get_y_units(info):
    """finds flux/reflectance units
       inputs: <info>: .fits header or .ascii metadata
       outputs: y_units
    """
    flux_id = ["ERG", "FLAM"] #IDs to look for units with
    #I know erg isn't the full unit, but it's a good indicator.
    norm_id = ["NORM", "REFLECTANCE"] #IDs to look for normalizations with
    if isinstance(info, float):
        y_units = (1*u.m/u.m).unit.decompose()
        print("y_units: normalized")
        
    elif isinstance(info, collections.OrderedDict): #From .ascii
        col_head = list(info.values())[0][0]
        if any(unit_id in col_head.upper() for unit_id in flux_id):
            y_unit = u.erg/(u.cm**2)/u.s/u.AA
        elif any(unit_id in col_head.upper() for unit_id in norm_id):
            y_units = (1*u.m/u.m).unit.decompose()
            print("y_units: normalized")
        else:
            print("WARNING: Could not parse flux units from file. Assuming erg/cm^2/s/A")
            y_units = u.erg/(u.cm**2)/u.s/u.AA

    elif isinstance(info, fits.header.Header):  #from .fits
        possible_keys = ['BUNIT','TUNIT2'] #maybe add more later
        keys = list(info.keys())
        values = list(info.values())
        for n in range(len(keys)):
            if any(key_id in keys[n] for key_id in possible_keys):
                if any(unit_id in values[n] for unit_id in flux_id):
                    if "10^20" in values[n]:
                        y_units = u.erg/(u.cm**2)/u.s/u.AA*10**20
                    else:
                        y_units = u.erg/(u.cm**2)/u.s/u.AA
                elif any(unit_id in values[n] for unit_id in norm_id):
                    y_units = (1*u.m/u.m).unit.decompose()
                    print("y_units: normalized")
                else:
                    print("WARNING: Could not parse flux units from file. Assuming erg/cm^2/s/A")
                    y_units = u.erg/(u.cm**2)/u.s/u.AA
        try:
            print("y_units:",y_units)
        except NameError:
            print("WARNING: Could not parse flux units from file. Assuming erg/cm^2/s/A")
            y_units = u.erg/(u.cm**2)/u.s/u.AA

    return y_units

def read_spectra(spectra_file):
    """reads in all inportant data from spectra file (Works for .ascii and .fits 2 standards)
       inputs: <spectra_file>: path and file name to spectra
       outputs: wavelength (Quantity type), flux, flux_error, x_units, y_units
    """
    if spectra_file.endswith('.fits'):
        hdul = fits.open(spectra_file) #read in data
    #LCO fits standard:
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
            x_data = np.array(list(n[0] for n in data))
            y_data = np.array(list(n[1] for n in data))
            
            if len(data[0]) > 2:
                flux_error = np.array(list(n[2] for n in data))
            else:
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
        
    elif spectra_file.endswith('.txt'):
        data = open(spectra_file)
        x_data = np.array([])
        y_data = np.array([])
        flux_error = np.array([])
        for line in data:
            x_data = np.append(x_data, float(line.split()[0]))
            y_data = np.append(y_data, float(line.split()[1]))
            flux_error = np.append(flux_error, float(line.split()[2]))
        x_units = get_x_units(x_data)
        y_units = get_y_units(y_data[0])
        
    else:
        raise ImportError("Invalid input file type")

    #eliminate negative error values 
    y_data[np.logical_not(y_data >= 0)] = np.nan
    flux_error[np.logical_not(flux_error >= 0)] = np.nan

    wavelength = (x_data*x_units).to(u.AA)
    #convert all wavelengths to Angstroms because it's easy to deal with that way
    flux = y_data*y_units

    return wavelength, flux, flux_error, x_units, y_units


def smooth(x,ydata, window=20):
    """uses boxcar averaging to smooth flux data
       inputs: <ydata>: raw flux data
               [window]: size of smoothing window (default = 20)
       outputs: smoothed flux data
    """

    if len(ydata) < window:
        raise ValueError("Input vector must be bigger than window size.")

    if window < 3:
        return x,ydata

    #if window % 2 != 0: I believe Box 1D kernel handles this already
    #    window += 1

    return x[window:-window], convolve(ydata, Box1DKernel(window))[window:-window] #boxcar average data

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

    #path = '/home/adam/test_spectra/' #will make more general file passing later
    path = '/home/atedeschi/test_spectra/'
    #spectra = '467309/20180613/ntt467309_U_ftn_20180613_merge_2.0_58283_1_2df_ex.fits'
    #spectra = '1627/20180618/ntt1627_ftn_20180618_merge_6.0_58288_2_2df_ex.fits'
    #spectra = 'calspec/eros_visnir_reference_to1um.ascii'
    #spectra = 'calspec/alpha_lyr_stis_008.fits' #vega?
    #spectra = 'calspec/bd17d4708_stis_001.fits'        
    spectra = 'a001981.4.txt'
    
    #sol_ref = 'calspec/sun_mod_001.fits'
    #sol_ref = 'Solar_analogs/HD209847/nttHD209847_ftn_20180625_merge_2.0_58295_2_2df_ex.fits'
    #sol_ref =  'solar_standard_V2.fits'
    sol_ref = 'calspec/sun_reference_stis_001.fits'

    window = 2 # 2 for eros ascii file. 20 for most others
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        x,y,yerr,x_units,y_units = read_spectra(path+spectra)
    xsmoothed,ysmoothed = smooth(x,y,window) #[window/2:-window/2]

    #Smoothing may cause artifacts at data ends.

    window_ref = 2
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        x_ref,y_ref,yerr_ref,x_ref_units,y_ref_units = read_spectra(path+sol_ref)
    x_refsmoothed,y_refsmoothed = smooth(x_ref, y_ref, window_ref)

    #print(x.shape, y.shape, x_ref.shape, y_ref.shape, ysmoothed.shape, y_refsmoothed.shape)

    normy, normyerr = normalize(xsmoothed,ysmoothed,yerr) #normalizing data
    normy_ref,normerr_ref = normalize(x_refsmoothed,y_refsmoothed,yerr_ref)

    #print(yerr)
    #print(normyerr)

    #plotting data
    plot_spectra(xsmoothed,normy)
    plot_spectra(x_refsmoothed,normy_ref)
    plt.show()
