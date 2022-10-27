import os
import argparse
from sys import argv, exit
from datetime import datetime, timedelta
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "neox.settings")
from django.conf import settings
import django
django.setup()

from photometrics.catalog_subs import *
from core.views import determine_images_and_catalogs
from astrometrics.ephem_subs import horizons_ephem

from numpy import unique
from astropy.table import Table, Column
from astropy.time import Time
from astropy.io import fits

import astropy.units as u
from astropy.coordinates import SkyCoord

import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from scipy.odr import Model, Data, ODR
from scipy import interpolate
import copy

def run(config):

    # Review the available dataset and return a list of the images and catalogs
    images, catalogs = determine_images_and_catalogs(None, config['dataroot'],
                                                     red_level='e92')

    # Extract the required data from the set of catalogs
    full_dataset, full_photastro_datatables = load_catalog_data(images, catalogs)

    # Store the target name in the config for future reference.
    # The name used for the first frame in the dataset is assumed to be the
    # target throughout
    config['target_name'] = full_dataset['target_name'][0]

    obs_filters = unique(full_dataset['filter'])
    if config['filters'] not in obs_filters:
        obs_str = ",".join(obs_filters)
        req_str = ",".join(config['filters'])
        raise IOError(f"Requested filters ({req_str}) not in observed filters ({obs_str})")

    # Loop over requested filters making ZP and WCS m
    for obs_filter in config['filters']:
        mask = full_dataset['filter'] == obs_filter
        dataset = full_dataset[mask]

        photastro_datatables = []
        for i, tab in enumerate(full_photastro_datatables):
             if mask[i] == True:
                photastro_datatables.append(tab)
        print(f"Analyzing filter {obs_filter}, #rows={len(dataset)}, {len(photastro_datatables)}")

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

        # Identify the row index of the target in the datatable for each frame,
        # based on the predicted position of the target
        target_index = identify_target_in_frames(dataset, photastro_datatables)
        check_target_index(target_index)

        # Extract table of target flux radius and flux, flux_err in all apertures
        target_data = extract_target_photometry(dataset, photastro_datatables, target_index)

        num_apers = list(set([len(t[0]['obs_mag']) for t in photastro_datatables]))
        if len(num_apers) != 1:
            raise IOError('Inconsistent number of apertures')
        config['num_apers'] = num_apers[0]

        # Output results table & plots
        output_target_data_table(config, target_data)
        output_ascii_target_data_table(config, target_data, aperture=4)
        plot_target_radius(config, target_data)
        plot_multi_aperture_lightcurve(config, target_data)

def check_target_index(target_index):
    """Function catches instance where the target has not been identified in
    any frames"""

    idx = np.array(target_index)
    if (idx == -99.0).all():
        raise IOError('Target not identified in any frames')

def plot_multi_aperture_lightcurve(config, target_data):
    """Function to plot the lightcurve from multiple apertures"""

    # Exclude datapoints with suspicious values:
    idx1 = np.where((target_data['mag_aperture_0'] > 0.0))[0]
    idx2 = np.where((target_data['mag_aperture_0'] < 30.0))[0]
    valid = list(set(idx1).intersection(set(idx2)))

    # Generate an array of DateTime objects for all datapoints
    dates = convert_timestamps(target_data['obs_midpoint'].data)
    date_format = get_date_format(dates)

    plot_errors = True
    naper = config.get('num_apers', 20)
    colour_codes = ['#FA281B', '#FA731B', '#FAA91B', '#FAD51B', '#CBFA1B',
                    '#91FA1B', '#3BD718', '#18D797', '#18D7C9', '#18B1D7',
                    '#1897D7', '#1878D7', '#183ED7', '#9438E0', '#BD38E0',
                    '#C914CC', '#CC1486', '#CC1462', '#BA061F', '#BA9F06']
    symbols = ['.','v','^','<','>','s','p','*','H','d',
               '.','v','^','<','>','s','p','*','H','d']
    fig = plt.figure(3,(20,15))
    ax = fig.add_subplot(111)
    plt.rcParams.update({'font.size': 16})
    plt.rcParams['axes.formatter.useoffset'] = False

    for i in range(0,naper,1):
        if plot_errors:
            plt.errorbar(dates[valid], target_data['mag_aperture_'+str(i)][valid],
                            yerr=target_data['mag_err_aperture_'+str(i)][valid],
                            c=colour_codes[i], marker=symbols[i], label='Aperture '+str(i),
                            ls='none')
        else:
            plt.plot(dates[valid], target_data['mag_aperture_'+str(i)][valid],
                 c=colour_codes[i], marker=symbols[i], label='Aperture '+str(i))
    plt.xlabel('Obs midpoint [UTC]')
    plt.ylabel('Mag')

    # Reformat x-axis datetime entries
    ax.xaxis.set_major_formatter(DateFormatter(date_format))
    ax.fmt_xdata = DateFormatter(date_format)
    fig.autofmt_xdate()

    plt.yticks(rotation = 25)
    [xmin,xmax,ymin,ymax] = plt.axis()
    #xmax = xmax*1.05   # Offset to allow for legend
    plt.subplots_adjust(bottom=0.15, left=0.05)
    plt.axis([xmin,xmax,ymax,ymin]) # Invert magnitude axis
    plt.title(config['target_name']+' multi-aperture lightcurves')
    plt.grid()

    # Add the legend outside the plot face
    box = ax.get_position()
    ax.set_position([box.x0, box.y0 + box.height * -0.025,
             box.width, box.height * 0.95])

    l = ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.2), ncol=6)

    l.legendHandles[0]._sizes = [50]
    if len(l.legendHandles) > 1:
        l.legendHandles[1]._sizes = [50]

    plt.rcParams.update({'legend.fontsize':12})

    bandpass = target_data['filter'][0]
    plt.savefig(os.path.join(config['dataroot'], config['target_name']
                             + '_multi_lightcurve_'+str(bandpass)+'.png'))
    plt.close(3)

def plot_target_radius(config, target_data):
    """Function to plot the extracted radius of the target as a function of time"""

    # Generate an array of DateTime objects for all datapoints
    dates = convert_timestamps(target_data['obs_midpoint'].data)
    date_format = get_date_format(dates)

    fig = plt.figure(3,(20,10))
    ax = fig.add_subplot(111)
    plt.rcParams.update({'font.size': 16})
    plt.rcParams['axes.formatter.useoffset'] = False

    plt.plot(dates, target_data['flux_radius'], 'ms',
                label='Target radius')
    plt.plot(dates, target_data['fwhm'], 'gd',
                label='FWHM', alpha=0.5)
    plt.xlabel('Obs midpoint [UTC]', fontsize=16)
    plt.ylabel('Radius [arcsec]', fontsize=16)

    # Reformat x-axis datetime entries
    ax.xaxis.set_major_formatter(DateFormatter(date_format))
    ax.fmt_xdata = DateFormatter(date_format)
    fig.autofmt_xdate()

    plt.xticks(rotation = 25, ha='right', fontsize=16)
    plt.yticks(rotation = 25, fontsize=16)
    plt.subplots_adjust(bottom=0.25)
    plt.title(config['target_name']+' flux radius as a function of time')
    plt.grid()
    plt.legend()
    bandpass = target_data['filter'][0]
    plt.savefig(os.path.join(config['dataroot'],
                config['target_name']+'_flux_radius_curve_'+str(bandpass)+'.png'))
    plt.close(3)

def convert_timestamps(timestamps):
    """Function to convert an array of timestamps in string format to DateTime
    objects
    Expected input format is %Y-%m-%dT%H:%M:%S.%f
    Outputs an array of DateTime objects
    """
    dates = []
    for ts in timestamps:
        if type(ts) == np.bytes_:
            ts = ts.decode('UTF-8')
        dates.append(datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%f"))
    dates = np.array(dates)

    return dates

def get_date_format(dates):
    """Function to format date strings for plotting, extracted from NEOexchange
    Input should be an array of DateTime objects
    Returns the format string to be used in matplotlib
    """
    start = dates[0]
    end = dates[-1]
    time_diff = end - start
    if time_diff > timedelta(days=3):
        return "%Y/%m/%d"
    elif time_diff > timedelta(hours=6):
        return "%m/%d %H:%M"
    elif time_diff > timedelta(minutes=30):
        return "%H:%M"
    else:
        return "%H:%M:%S"

def set_output_file_path(config, descriptor):

    bandpass = descriptor['filter'][0]
    filepath = os.path.join(config['dataroot'],
                config['target_name']+'_data_'+str(bandpass)+'.fits')
    return filepath


def output_target_data_table(config, target_data):
    """Function to output the target data table as a FITS binary table"""

    filepath = set_output_file_path(config, target_data)

    # This is done to avoid concatenation of files that are produced more than
    # once.
    if os.path.isfile(filepath):
        os.remove(filepath)

    target_data.write(filepath, format='fits')

def output_ascii_target_data_table(config, target_data, aperture=4):
    """Function to output the target data table in an ASCII table, with space
    separators, with the following columns:
    MJD time, magnitude, magnitude error
    Row 1 of the file starts with a '#' symbol and a header with the
    column names

    The aperture parameter determines the number of the aperture selected for
    output.  The numering system is the Python array index, i.e. from zero
    and the default is aperture[4].
    """

    # Follow the default filename convention, but replacing the extension:
    filepath = set_output_file_path(config, target_data)
    filepath = filepath.replace('.fits', '.txt')

    # Overwrite any pre-exisiting files:
    if os.path.isfile(filepath):
        os.remove(filepath)

    # Sort into time order:
    order = np.argsort(target_data['mjd'].data)

    # Output data table:
    f = open(filepath,'w')
    f.write('#   MJD     Magnitude     Magnitude_error\n')
    for row in order:
        if target_data['mag_aperture_'+str(aperture)][row] < 0.0 or \
            target_data['mag_aperture_'+str(aperture)][row] > 25.0:
            prefix = '#'
        else:
            prefix = ''

        # Zero pad the timestamps
        ts = target_data['mjd'][row]
        f.write("{}{:.6f}   {:.5f}   {:.5f}\n".format(prefix, ts, \
                    target_data['mag_aperture_'+str(aperture)][row], \
                    target_data['mag_err_aperture_'+str(aperture)][row]))
    f.close()

def extract_target_photometry(dataset, photastro_datatables, target_index):
    """Function to extract the multi-aperture photometry of the target from
    the photometry datatables for each frame.
    """

    data = []

    # Figure out the number of apertures in use from the first entry in the
    # table
    naper = len(photastro_datatables[0]['obs_mag'][0].tolist())

    # Loop over all images in the dataset:
    # NOTE obs_midpoint datetime objects are converted to strings here because
    # this is necessary for output to a FITS table later on.
    for i in range(0,len(dataset),1):
        j = target_index[i]
        if j >= 0:
            table = photastro_datatables[i]
            entry = [dataset['filename'][i], dataset['mjd'][i],
                     dataset['obs_midpoint'][i].strftime("%Y-%m-%dT%H:%M:%S.%f"),
                     dataset['exptime'][i],
                     dataset['filter'][i],
                     table['obs_ra'][j], table['obs_dec'][j],
                     table['flux_radius'][j], dataset['fwhm'][i]]
            mags = table['obs_mag'][j].tolist()
            merrs = table['obs_mag_err'][j].tolist()
            for k in range(0,naper,1):
                entry.append(mags[k])
                entry.append(merrs[k])
            data.append(entry)
    data = np.array(data)

    # Extract the number of apertures to expect:
    naper = len(table['obs_mag'][0])
    nother = 9

    # Format as an astropy Table:
    column_list = [ Column(data[:,0], name='filename', dtype=str),
                    Column(data[:,1], name='mjd', dtype=np.float64),
                    Column(data[:,2], name='obs_midpoint', dtype=str),
                    Column(data[:,3], name='exptime', dtype=np.float64),
                    Column(data[:,4], name='filter', dtype=str),
                    Column(data[:,5], name='obs_ra', dtype=np.float64),
                    Column(data[:,6], name='obs_dec', dtype=np.float64),
                    Column(data[:,7], name='flux_radius', dtype=np.float64),
                    Column(data[:,8], name='fwhm', dtype=np.float64)]
    ap = -1
    for col in range(nother,nother+(naper*2),2):
        ap += 1
        column_list.append(Column(data[:,col], name='mag_aperture_'+str(ap),
                            dtype=np.float64))
        column_list.append(Column(data[:,col+1], name='mag_err_aperture_'+str(ap),
                            dtype=np.float64))

    return Table(column_list)

def identify_target_in_frames(dataset, photastro_datatables):
    """Function draws on JPL Horizons to predict the expected locations of
    Didymos at the times of each frame.
    The target is located in each frame by identifying the object in the
    detected sources table with the smallest angular separation from the
    predicted location.

    Returns a list of the target's array row index in each of the tables in
    photastro_datatables
    """

    target_index = []

    # Astrometric tolerance: maximum allowed radial separation for an object to
    # be considered to be a match:
    tolerance = (5.0/3600.0)*u.deg

    first = dataset['obs_midpoint'].min()
    last = dataset['obs_midpoint'].max()
    # Compute ephemeris for Didymos=65803 for length of exposure time range
    # Note that the interval of calculation must be '1m' or greater, or
    # Horizons returns a ValueError, leading to a spurious error of
    # 'Ambiguous object'
    site_codes = list(set(dataset['site_code']))
    if len(site_codes) != 1:
        raise IOError('Multiple site codes found')
    site_code = site_codes[0]
    ephem = horizons_ephem('65803',
                    first-timedelta(minutes=1), last+timedelta(minutes=1),
                    site_code, '1m', alt_limit=20)
    # Loop over all images in the dataset:
    for i in range(0,len(dataset),1):

        # Extract the sky coordinates of all objects detected in this frame:
        table = photastro_datatables[i]
        detected_pos = SkyCoord(table['obs_ra'], table['obs_dec'], unit=u.deg)

        if len(detected_pos) > 0:
            midpoint = dataset['obs_midpoint'][i]

            # Find index of nearest in time from the ephememeris line, and use it
            # to extract the predicted sky position of the target in this frame
            horizons_index = np.abs(midpoint-ephem['datetime'].datetime).argmin()
            horizons_pos = SkyCoord(ephem['RA'][horizons_index],
                                    ephem['DEC'][horizons_index], unit=u.deg)

            # Calculate the radial separations of all detected sources from the
            # predicted position of the object, and select the closest entry
            sep_r = horizons_pos.separation(detected_pos).to(u.arcsec)
            lco_index = np.where(sep_r == sep_r.min())[0][0]

            # If the index is within a reasonable tolerance store the index,
            # otherwise store a -99 entry.
            print(f"{i:>3d} {dataset[i]['filename']} {sep_r[lco_index]:.3f} {tolerance.to(u.arcsec)} x,y= {table[lco_index]['ccd_x']:.3f}, {table[lco_index]['ccd_y']:.3f}")
            if sep_r[lco_index] <= tolerance:
                target_index.append(lco_index)
            else:
                target_index.append(-99)

        # If no stars were detected in this frame, move on:
        else:
            target_index.append(-99)

    return target_index

def apply_corrected_wcs(dataset, photastro_datatables):
    """Function recalculates the RA, Dec positions for all objects detected
    in frames where the original WCS fit failed, using the original detected
    image coordinates, and the revised WCS"""

    for i in range(0,len(dataset),1):
        if dataset['astrometric_fit_status'][i] > 0:
            table = photastro_datatables[i]
            wcs = dataset['wcs'][i]
            sky = wcs.pixel_to_world(table['ccd_x'], table['ccd_y'])
            table['obs_ra'] = sky.ra.deg
            table['obs_dec'] = sky.dec.deg
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
        if dataset['astrometric_fit_status'][i] > 0:
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
        if dataset['astrometric_fit_status'][i] == 0:
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
            table['obs_mag'] = table['obs_mag'] + new_zp
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

    if len(valid) == 0:
        raise ValueError('No frames have a valid zeropoint measurement; no fit is possible')

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
    Frame index, filename, obs_midpoint (datetime), timestamp (MJD), site code,
    zeropoint, zeropoint error, exposure_time,
    CRVAL1, CRVAL2, CRPIX1, CRPIX2, CD1_1, CD1_2, CD2_1, CD2_2,
    astrometric_fit_status

    Returns:
        an astropy Table with each image represented as a row
    """

    # Default configuration:
    flag_filter = 3

    # Compile dataset of zeropoints and WCS data per frame
    data = []
    photastro_datatables = []
    for i,catalog in enumerate(catalogs):

        fits_header, fits_table, catalog_type = open_fits_catalog(catalog)

        header = get_catalog_header(fits_header, catalog_type)
        table = get_catalog_items_new(header, fits_table, catalog_type, flag_filter)

        target_name = fits_header['OBJECT'].replace(' ','_').replace(')','_').replace('(','_')
        header['target_name'] = target_name

        # Get the zeropoint data, if available, from the e92 FITS image header,
        # because it isn't currently written to the LDAC header.
        imheader = fits.getheader(images[i])
        try:
            zp = imheader['L1ZP']
            zperr = imheader['L1ZPERR']
        except KeyError:
            zp = -99.0
            zperr = -99.0

        # Add the flux_radius data to the data table since it isn't extracted
        # by default.
        flux_radii_column = get_flux_radii(fits_table, flag_filter)
        table.add_column(flux_radii_column, index=-1)

        # Compile frame information
        ts = Time(header['obs_midpoint'], format='datetime')
        data.append([i, header['framename'],
                     header['obs_midpoint'],
                     ts.mjd,
                     header['site_code'], header['filter'],
                     zp, zperr,
                     header['exptime'],
                     header['wcs'], header['astrometric_fit_status'],
                     header['target_name'], header['fwhm']])

        photastro_datatables.append(table)
    data = np.array(data)

    # Format as an astropy Table:
    dataset = Table([
                    Column(data[:,0], name='frame_index', dtype=np.int32),
                    Column(data[:,1], name='filename', dtype=str),
                    Column(data[:,2], name='obs_midpoint'),
                    Column(data[:,3], name='mjd', dtype=np.float64),
                    Column(data[:,4], name='site_code'),
                    Column(data[:,5], name='filter'),
                    Column(data[:,6], name='zeropoint', dtype=np.float64),
                    Column(data[:,7], name='zeropoint_err', dtype=np.float64),
                    Column(data[:,8], name='exptime', dtype=np.float64),
                    Column(data[:,9], name='wcs'),
                    Column(data[:,10], name='astrometric_fit_status', dtype=np.int32),
                    Column(data[:,11], name='target_name', dtype=str),
                    Column(data[:,12], name='fwhm', dtype=np.float64),
                    ])

    return dataset, photastro_datatables

def get_flux_radii(fits_table, flag_filter):
    """Function to extract the flux radius data from the fits_table, since
    it isn't retrieved by default.  This function somewhat overlaps the
    functionality of catalog_subs.get_catalog_items_new, in order to
    apply the same filtering to the data.  It could be merged with that
    function, but this has been postponed for the time being to avoid
    unnecessary complications elsewhere in the pipeline.
    """

    # Amended to add the flux radius:
    tbl_mapping = table_dict = OrderedDict([
                    ('ccd_x'         , 'XWIN_IMAGE'),
                    ('ccd_y'         , 'YWIN_IMAGE'),
                    ('obs_ra'        , 'ALPHA_J2000'),
                    ('obs_dec'       , 'DELTA_J2000'),
                    ('obs_ra_err'    , 'ERRX2_WORLD'),
                    ('obs_dec_err'   , 'ERRY2_WORLD'),
                    ('major_axis'    , 'AWIN_IMAGE'),
                    ('minor_axis'    , 'BWIN_IMAGE'),
                    ('ccd_pa'        , 'THETAWIN_IMAGE'),
                    ('obs_mag'       , 'FLUX_APER'),
                    ('obs_mag_err'   , 'FLUXERR_APER'),
                    ('obs_sky_bkgd'  , 'BACKGROUND'),
                    ('flags'         , 'FLAGS'),
                    ('flux_max'      , 'FLUX_MAX'),
                    ('threshold'     , 'MU_THRESHOLD'),
                    ('flux_radius'   , 'FLUX_RADIUS'),
                 ])

    new_table = subset_catalog_table(fits_table, tbl_mapping)

    # Rename columns
    for new_name in tbl_mapping:
        new_table.rename_column(tbl_mapping[new_name], new_name)

    # Filter on flags first
    if 'flags' in tbl_mapping:
        new_table = new_table[new_table['flags'] <= flag_filter]

    # Filter out -ve fluxes
    good_flux_mask = new_table['obs_mag'] > 0.0
    if len(good_flux_mask.shape) == 2:
        good_flux_mask = good_flux_mask.any(axis=1)
    new_table = new_table[good_flux_mask]

    return new_table['flux_radius']

def get_args(args):

    parser = argparse.ArgumentParser(description='Extract multi-aperture photometry',
                                     usage='%(prog)s [--filters]> <dataroot>')
    parser.add_argument('dataroot', default=settings.DATA_ROOT, help='Dataroot path')
    parser.add_argument('--filters', nargs='+', default=['w', ], help='Filters to analyze (default: %(default)s)')

    options = parser.parse_args(args)
    config = vars(options)

    return config


if __name__ == '__main__':
    config = get_args(argv[1:])
    run(config)
