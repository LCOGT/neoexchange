import os
from sys import argv
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "neox.settings")
from django.conf import settings
import django
django.setup()

from photometrics.catalog_subs import *
from core.views import determine_images_and_catalogs

from astropy.table import Table, Column
from astropy.time import Time

import matplotlib.pyplot as plt
from scipy.odr import Model, Data, ODR
from scipy import interpolate
import copy

def run(config):

    # Review the available dataset and return a list of the images and catalogs
    images, catalogs = determine_images_and_catalogs(None, config['dataroot'],
                                                     red_level='e92')

    # Extract the required data from the set of catalogs
    dataset, photastro_datatables = load_catalog_data(images, catalogs)

    # Interpolate the trend in photometric zeropoint as a function of time
    zp_model = interpolate_with_time(config, dataset['mjd'], dataset['zeropoint'],
                                    diagnostics=True,
                                    plot_labels=['MJD', 'Zeropoint [mag]'],
                                    plot_file='zeropoint_trend.png')

    # Apply the revised zeropoints to the obs_mag column for
    # each photastro_datatable
    photastro_datatables = apply_new_zeropoints(dataset, photastro_datatables, zp_model)

    # Interpolate the trends in the WCS parameters as functions of time
    wcs_model = interpolate_wcs_with_time(config, dataset,
                                                    diagnostics=True)

    # Apply the astrometric models to create a valid WCS for those frames
    # which previously had none
    dataset = correct_invalid_wcs(dataset, wcs_model)

    # Apply the revised WCS to the source positions (ALPHA_J2000, DELTA_J2000)
    # columns in each photastro_datatable
    photastro_datatables = apply_corrected_wcs(dataset, photastro_datatables)

    # Identify the target in each frame

    # Extract table of target flux radius and flux, flux_err in all apertures

    # Output results table & plots
    
def apply_corrected_wcs(dataset, photastro_datatables):
    """Function recalculates the RA, Dec positions for all objects detected
    in frames where the original WCS fit failed, using the original detected
    image coordinates, and the revised WCS"""

    for i in range(0,len(dataset),1):
        # CHECK IF WCS VALID HERE
        valid = True
        if not valid:
            table = photastro_datatables[i]
            wcs = dataset['wcs'][i]
            sky = wcs.pixel_to_world(table['XWIN_IMAGE'], table['YWIN_IMAGE'])
            table['ALPHA_J2000'] = sky.ra.deg
            table['DELTA_J2000'] = sky.dec.deg
            photastro_datatables[i] = table

    return photastro_datatables

def correct_invalid_wcs(dataset, wcs_model):
    """Function selects out the frames for which the original WCS fit failed,
    and uses an interpolated model to generate a revised WCS.
    This function updates the input dataset
    Frames with an existing valid WCS are not altered.
    Note that the WCS error code is NOT changed, so that this parameter
    can be used later to figure out which data tables need positions updated.
    """

    (ra_model, dec_model, xcentre, ycentre) = wcs_model

    for i in range(0,len(dataset),1):
        # CHECK IF WCS VALID HERE
        valid = True
        if not valid:
            wcs = dataset['wcs'][i]
            wcs.wcs.crpix = [ycentre, xcentre]
            crval1 = ra_model(dataset['mjd'][i])
            crval2 = dec_model(dataset['mjd'][i])
            wcs.wcs.crval = [crval1, crval2]
            dataset['wcs'][i] = wcs

    return dataset

def interpolate_wcs_with_time(config, dataset, diagnostics=True):

    # Get size of frame from first entry and calculate the pixel location
    # of the frame centre - ASSUMES ALL FRAMES ARE THE SAME SIZE
    ysize = dataset['wcs'][0].array_shape[0]
    xsize = dataset['wcs'][0].array_shape[1]
    ycentre = int(round((float(ysize) / 2.0),0))
    xcentre = int(round((float(xsize) / 2.0),0))

    # Calculate the RA, Dec of the pixel centre of all frames, using the
    # existing WCS if valid
    frame_centres = []
    for i in range(0,len(dataset),1):
        # CHECK IF WCS VALID HERE
        valid = True
        if valid:
            s = dataset['wcs'][i].pixel_to_world(ycentre, xcentre)
            c = [s.ra.deg, s.dec.deg]
        else:
            c = [-99.0, -99.0]
        frame_centres.append(c)
    frame_centres = np.array(frame_centres)

    ra_model = interpolate_with_time(config, dataset['mjd'], frame_centres[:,0],
                                data_err=None, diagnostics=True,
                                plot_labels=['MJD', 'RA [deg]'],
                                plot_file='ra_trend.png')
    dec_model = interpolate_with_time(config, dataset['mjd'], frame_centres[:,1],
                                data_err=None, diagnostics=True,
                                plot_labels=['MJD', 'Dec [deg]'],
                                plot_file='dec_trend.png')

    return [ra_model, dec_model, xcentre, ycentre]

def apply_new_zeropoints(dataset, photastro_datatables, zp_model):
    """Function to apply the revised photometric zeropoints to the obs_mag
    column of the photometry datatable for each frame.

    Note that this revision is only necessary for those datapoints where no
    valid zeropoint was calculated previously - for these frames, the obs_mag
    returned in the table will be an instrumental magnitude only, calculated
    using the SExtractor default zeropoint of 0.0.
    """

    # Loop over all frames in the dataset
    for i in range(0, len(dataset), 1):
        if dataset['zeropoint'][i] == -99.0:
            new_zp = zp_model(dataset['mjd'][i])
            table = photastro_datatables[i]
            table['obs_mag'] + new_zp
            photastro_datatables[i] = table

    return photastro_datatables

def calc_zeropoint_per_frame(config, dataset, zp_model, diagnostics=False):
    """Function to apply the model of the photometric zeropoint as a function
    of time to all frames in the dataset.
    Function updates the input dataset
    """

    # Update the zeropoints from the model:
    orig_zp = dataset['zeropoints']
    dataset['zeropoints'] = zp_model(dataset[mjd])

    # Optional diagnostic plot
    if diagnostics:
        fig = plt.figure(1,(10,10))
        # Plot errorbars if sufficient valid data are available:
        plt.plot(orig_times, orig_zp, 'gd', alpha=0.2, label='Original data')
        plt.plot(dataset['mjd'], dataset['zeropoints'], 'r.', label='Corrected data')
        ydata = model(dataset['mjd'])
        plt.plot(times, ydata, 'k-')
        plt.xlabel('MJD')
        plt.ylabel('Zeropoint [mag]')
        plt.xticks(rotation = 25)
        plt.grid()
        plt.legend()
        plt.savefig(os.path.join(config['dataroot'], 'revised_zeropoints.png'))
        plt.close(1)

    return dataset

def interpolate_with_time(config, times, data, data_err=None, diagnostics=False,
                            plot_labels=['MJD', 'Data'], plot_file=None):
    """Function to perform a 1D interpolation of the given 1D array of data
    as a function of time.
    """

    orig_data = copy.copy(data)
    orig_times = copy.copy(times)

    # Expect data array to have invalid values, which we eliminate:
    valid = np.where(data != -99.0)[0]

    # To ensure that the model covers the full range of times in the dataset,
    # there must be valid data at the 0th and -1th array entries.  If this is
    # not the case, we echo the nearest datapoints to the first and last ones:
    if 0 not in valid:
        data[0] = data[valid.min()]
    if (len(data)-1) not in valid:
        data[-1] = data[valid.max()]
    valid = np.where(data != -99.0)

    # Fit a 1D interpolation model
    model = interpolate.interp1d(times[valid], data[valid])

    # Optional diagnostic plot
    if diagnostics:
        fig = plt.figure(1,(10,10))
        # Plot errorbars if sufficient valid data are available:
        if data_err:
            try:
                plt.errorbar(times[valid], data[valid],
                             yerr=data_err[valid], fmt='.')
            except:
                plt.plot(times[valid], data[valid], 'r.')
        else:
            plt.plot(orig_times, orig_data, 'gd', alpha=0.2, label='Original data')
            plt.plot(times[valid], data[valid], 'r.', label='Fitted data')
        ydata = model(times)
        plt.plot(times, ydata, 'k-', label='Fitted model')
        plt.xlabel(plot_labels[0])
        plt.ylabel(plot_labels[1])
        plt.xticks(rotation = 25)
        plt.grid()
        plt.legend()
        if not plot_file:
            plt.savefig(os.path.join(config['dataroot'], 'interpolated_function.png'))
        else:
            plt.savefig(os.path.join(config['dataroot'], plot_file))
        plt.close(1)

    return model

def polynomial_func(p,data):
    """Polynomial function
    Expected function is of the form p[0]*data + p[1]
    """

    return np.polyval(p,data)

def load_catalog_data(images, catalogs):
    """Function to read in a set of e92 LDAC catalogs, extracting the data
    required to model the photometric zeropoint and astrometric parameters
    as a function of time:
    Frame index, filename, timestamp (MJD), zeropoint, zeropoint error,
    exposure_time,
    CRVAL1, CRVAL2, CRPIX1, CRPIX2, CD1_1, CD1_2, CD2_1, CD2_2

    Returns:
        an astropy Table with each image represented as a row
    """

    # Default configuration:
    flag_filter = 0

    # Compile dataset of zeropoints and WCS data per frame
    data = []
    photastro_datatables = []
    for i,catalog in enumerate(catalogs):

        fits_header, fits_table, catalog_type = open_fits_catalog(catalog)

        header = get_catalog_header(fits_header, catalog_type)
        table = get_catalog_items_new(header, fits_table, catalog_type, flag_filter)

        # Compile frame information
        ts = Time(header['obs_midpoint'], format='datetime')
        data.append([i, header['framename'], ts.mjd,
                     header['zeropoint'], header['zeropoint_err'],
                     header['exptime'],
                     header['wcs']])

        photastro_datatables.append(table)
    data = np.array(data)

    #### INJECTING TEST DATASET:
    #### Simulated zeropoints and zeropoint error
    data[:,3] = np.random.normal(loc=24.0, scale=0.5, size=len(data))
    data[:,4] = np.random.normal(loc=0.05, scale=0.02, size=len(data))
    invalid = np.arange(0,len(data),3)
    data[invalid,3] = -99.0
    data[invalid,4] = -99.0
    #### END simulated data

    # Format as an astropy Table:
    dataset = Table([
                    Column(data[:,0], name='frame_index', dtype=np.int32),
                    Column(data[:,1], name='filename', dtype=np.str),
                    Column(data[:,2], name='mjd', dtype=np.float64),
                    Column(data[:,3], name='zeropoint', dtype=np.float64),
                    Column(data[:,4], name='zeropoint_err', dtype=np.float64),
                    Column(data[:,5], name='exptime', dtype=np.float64),
                    Column(data[:,6], name='wcs'),
                    ])

    return dataset, photastro_datatables

def get_args():
    config = {}
    if len(argv) == 1:
        config['dataroot'] = input('Please enter the dataroot path: ')
    else:
        config['dataroot'] = argv[1]

    return config


if __name__ == '__main__':
    config = get_args()
    run(config)
