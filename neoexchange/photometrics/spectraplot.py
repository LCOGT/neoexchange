"""
convert 1D fits spectra into a readable plot
Author: Adam Tedeschi
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
import collections,warnings,re

#np.set_printoptions(threshold=np.inf)

def check_norm(values): #not perfect nor finished yet
    """checks with fits standard parsing and notifies if flux data has been normalized already
       input: <values>: array of text values in .fits header to parse
       ouptuts: boolean?
    """
    for value in values:
        if "NORMALIZED TO" in str(value).upper():
            normstr = value
            for s in normstr.split():
                try:
                    normval = float(s)
                    normloc = list(float(t) for t in re.findall(r'-?\d+\.?\d*',normstr))[-1] #reg. expres.
                    print("WARNING: Flux normalized to ", normval, " at ", normloc)
                except ValueError:
                    continue
    
def check_refl(x,y): #TEMPORARY CHECK
    if x[y.argmax()] > 6000*u.AA:
        print("Normalized Reflectance")

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
       inputs: <info>: .fits header, .ascii metadata, or point from .txt file
       outputs: y_units,factor
    """
    y_factor = 1
    flux_id = ["ERG", "FLAM"] #IDs to look for units with
    #I know erg isn't the full unit, but it's a good indicator.
    norm_id = ["NORM", "UNITLESS", "NONE"] #IDs to look for normalizations with
    refl_id = ["REFLECT"] #IDs to look for normalized reflectance
 
    if isinstance(info, float): #from .txt file (assuming normalized reflectance)
        y_units = u.def_unit("Normalized_Reflectance",(1*u.m/u.m).unit.decompose())
        print("y_units: ",y_units)
        
    elif isinstance(info, collections.OrderedDict): #from .ascii
        col_head = list(info.values())[0][0]
        if any(unit_id in col_head.upper() for unit_id in flux_id): #checking for flam
            y_units = u.erg/(u.cm**2)/u.s/u.AA
        elif any(unit_id in col_head.upper() for unit_id in norm_id): #checking for normalized
            if any(unit_id2 in col_head.upper() for unit_id2 in refl_id): #checking for normalization
                y_units = u.def_unit("Normalized_Reflectance",(1*u.m/u.m).decompose())
                print("y_units: ",y_units)
            else:   
                y_units = u.def_unit("Normalized_Flux",(1*u.m/u.m).decompose())
                print("y_units: normalized")
        elif any(unit_id in col_head.upper() for unit_id in relf_id): #checking for normalized reflectance
            y_units = u.def_unit("Normalized_Reflectance",(1*u.m/u.m).decompose())
            print("y_units: ",y_units)
        else:
            print("WARNING: Could not parse flux units from file. Assuming erg/cm^2/s/A")
            y_units = u.erg/(u.cm**2)/u.s/u.AA

    elif isinstance(info, fits.header.Header):  #from .fits
        possible_keys = ['BUNIT','TUNIT2'] #maybe add more later
        keys = list(info.keys())
        values = list(info.values())
        for n in range(len(keys)):
            if any(key_id in keys[n] for key_id in possible_keys):
                if any(unit_id in values[n].upper() for unit_id in flux_id):
                    if "10^20" in values[n]: #special LCO standard case
                        y_factor=10**20
                    y_units = u.erg/(u.cm**2)/u.s/u.AA
                elif any(unit_id in values[n].upper() for unit_id in norm_id):
                    if any(unit_id in col_head.upper for unit_id in refl_id): #checking for normalization
                        y_units = u.def_unit("Normalized_Reflectance",(1*u.m/u.m).decompose())
                        print("y_units: ",y_units)
                    else:
                        y_units = u.def_unit("Normalized_Flux",(1*u.m/u.m).decompose())
                        print("y_units: normalized")
                elif any(unit_id in col_head.upper for unit_id in refl_id): #checking for normalized reflectance
                    y_units = u.def_unit("Normalized_Reflectance",(1*u.m/u.m).decompose())
                    print("y_units: ",y_units)
                else:
                    print("WARNING: Could not parse flux units from file. Assuming erg/cm^2/s/A")
                    y_units = u.erg/(u.cm**2)/u.s/u.AA
        try:
            print("y_units:",y_units)
        except NameError:
            print("WARNING: Could not parse flux units from file. Assuming erg/cm^2/s/A")
            y_units = u.erg/(u.cm**2)/u.s/u.AA

    return y_units, y_factor

def read_object(hdr):
    """tries to identify object name from .fits header
       input: <hdr>: fits header
       output: obj_name
    """
    try:
        obj_name = hdr['OBJECT']
    except KeyError:
        obj_name = ""
    return obj_name

def read_spectra(spectra_file):
    """reads in all inportant data from spectra file (Works for .ascii 2 .fits standards, and .txt)
       inputs: <spectra_file>: path and file name to spectra
       outputs: wavelength (Quantity type), flux, flux_error, x_units, y_units, obj_name
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
        
        obj_name = read_object(hdr)
       
        x_units = get_x_units(x_data)
        y_units,y_factor = get_y_units(hdr)
        check_norm(hdul[0].header.values()) #check if data is already normalized
        
    elif spectra_file.endswith('.ascii'):
        data = ascii.read(spectra_file) #read in data
        #print(data.meta)
        #assuming 3 columns: wavelength, flux/reflectance, error
        x_data = data['col1'] #converting tables to ndarrays
        y_data = data['col2']
        flux_error = data['col3']
        x_units = get_x_units(x_data)
        y_units,y_factor = get_y_units(data.meta)
        obj_name = "" #TEMPORARY 

    elif spectra_file.endswith('.txt'):
        data = open(spectra_file) #read in data
        #assuming 3 columns: wavelength, reflectance, error
        x_data = np.array([])
        y_data = np.array([])
        flux_error = np.array([])
        for line in data:
            x_data = np.append(x_data, float(line.split()[0]))
            y_data = np.append(y_data, float(line.split()[1]))
            flux_error = np.append(flux_error, float(line.split()[2]))
        x_units = get_x_units(x_data)
        y_units,y_factor = get_y_units(y_data[0])
        obj_name = "" #TEMPORARY 
        
    else:
        raise ImportError("Invalid input file type")

    #eliminate negative error values 
    y_data[np.logical_not(y_data >= 0)] = np.nan
    flux_error[np.logical_not(flux_error >= 0)] = np.nan

    wavelength = (x_data*x_units).to(u.AA)
    #convert all wavelengths to Angstroms because it's easy to deal with that way
    flux = y_data*y_units

    if not obj_name:
        print("WARNING: Could not parse object name from file")
    else:
        print("Object: ", obj_name)
    
    check_refl(wavelength,flux)

    return wavelength, flux, flux_error, x_units, y_units, y_factor, obj_name


def smooth(x,y):
    """uses boxcar averaging to smooth flux data if necessary
       inputs: <ydata>: raw flux data
       outputs: smoothed flux data
    """
    #determining if smoothing is needed and to what degree
    stds=np.array([])
    normy = normalize(x,y)
    loc = 5
    while loc <= len(x):
        stds = np.append(stds,np.std(normy[loc-5:loc]).value)
        loc += int(len(x)/8)
    noisiness = np.nanmean(stds/((x[-1]-x[0])/len(x)).value)
    print(noisiness)

    if .0035 <= noisiness < .005:
        window = 15
    elif .005 <= noisiness < .01:
        window = 20
    elif noisiness >= .01:
        window = 30    
    else:
        print("smoothing: no")
        return x,y

    #smoothing
    print("smoothing: yes")
    return x[int(window/2):-int(window/2)], convolve(y, Box1DKernel(window))[int(window/2):-int(window/2)] #boxcar average data    

def normalize(x,y,wavelength=5500*u.AA):
    """normalizes flux data with a specific wavelength flux value
       inputs: <x>: wavelenth data (Quantity type)
               <y>: flux data (Quantity type)
               [wavelength]: target wavelength to normalize at (Quantity type)
       outputs: normalized flux data
    """
    normval = y[np.abs(x-wavelength).argmin()] #uses closest data point to target wavelength
    if normval == 0:
        normval = 1
    return y/normval #REMEMBER to normalize y-units too
    
def plot_spectra(x,y,y_units,ax,title, ref=0, norm=0,):
    """plots spectra data
       imputs: <x>: wavelength data for x axis
               <y>: flux data for y axis
               <ax>: matplotlib axis
               <title>: plot title (shoudl be object)
               [ref]: 1 for sol_ref, 0 for asteroid
               [norm]: normalizes data when set to 1
    """
    
    if norm == 1:
        yyy = normalize(x,y)
    else:
        yyy = y
    
    ax.plot(x,yyy,linewidth=1)
    ax.set_xlabel(r"wavelength ($\AA$)")
    ax.set_ylabel(y_units)
    if title:
        ax.set_title(title)
    else:
        if ref:
            ax.set_title("Solar_Analog")
        else:
            ax.set_title("Asteroid")

if __name__== "__main__":

    #path = '/home/adam/test_spectra/' #will make m9ore general file passing later
    path = '/home/atedeschi/test_spectra/'
    #spectra = '467309/20180613/ntt467309_U_ftn_20180613_merge_2.0_58283_1_2df_ex.fits'
    #spectra = '1627/20180618/ntt1627_ftn_20180618_merge_6.0_58288_2_2df_ex.fits'
    #spectra = '60/ntt60_ftn_20180612_merge_2.0_58282_1_2df_ex.fits'
    #spectra = '16/ntt16_ftn_20180606_merge_2.0_58276_1_2df_ex.fits'
    #spectra = 'calspec/eros_visnir_reference_to1um.ascii'
    #spectra = 'calspec/alpha_lyr_stis_008.fits' #vega?
    #spectra = 'calspec/bd17d4708_stis_001.fits'        
    spectra = 'a001981.4.txt'
    
    #sol_ref = 'calspec/sun_mod_001.fits'
    sol_ref = 'Solar_analogs/HD209847/nttHD209847_ftn_20180625_merge_2.0_58295_2_2df_ex.fits'
    #sol_ref =  'solar_standard_V2.fits'
    #sol_ref = 'calspec/sun_reference_stis_001.fits'

    #window = 2 
    print("\nasteroid: ")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        x,y,yerr,x_units,y_units,y_factor, obj_name= read_spectra(path+spectra)
    xsmoothed,ysmoothed = smooth(x,y)#,window) #[window/2:-window/2]

    print("\nreference star: ")
    #window_ref = 2
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        x_ref,y_ref,yerr_ref,x_ref_units,y_ref_units,y_factor_ref, obj_name_ref = read_spectra(path+sol_ref)
    x_refsmoothed,y_refsmoothed = smooth(x_ref, y_ref)#,window_ref)
    
    normyerr = normalize(x,yerr) #remember to normalize y-units too
    normyerr_ref = normalize(x_ref,yerr_ref)

    #print(x.shape, y.shape, x_ref.shape, y_ref.shape, ysmoothed.shape, y_refsmoothed.shape)

    #normy, normyerr = normalize(xsmoothed,ysmoothed,yerr) #normalizing data
    #normy_ref,normerr_ref = normalize(x_refsmoothed,y_refsmoothed,yerr_ref)

    #print(yerr)
    #print(normyerr)

    #plotting data
    #(for 2 spectra)
    fig, ax = plt.subplots(nrows=2,sharex=True)
    plot_spectra(xsmoothed,ysmoothed/y_factor,y_units.to_string('latex'),ax[0], obj_name, ref=0)
    plot_spectra(x_refsmoothed,y_refsmoothed/y_factor_ref,y_ref_units.to_string('latex'),ax[1], obj_name_ref, ref=1)
    plt.tight_layout(pad=1, w_pad=.5, h_pad=.5)
    
    plt.show()
