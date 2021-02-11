import requests
from astropy import wcs
from astropy.wcs import FITSFixedWarning
from astropy.io import fits
from astropy.table import Table
import os
from glob import glob
from subprocess import call
import warnings


def find_images(dest_dir):
    fits_files = glob(dest_dir+'/*g00.fits')
    fits_files.sort()
    return fits_files

def make_payload(image_catalog, amg_header):

    # Squelch astropy warning

    warnings.simplefilter('ignore', category = FITSFixedWarning)
    w = wcs.WCS(amg_header)

    pixel_scale= wcs.utils.proj_plane_pixel_scales(w).mean()*3600.

    catalog_payload = {'X': list(image_catalog['XWIN_IMAGE']),
                           'Y': list(image_catalog['YWIN_IMAGE']),
                           'FLUX': list(image_catalog['FLUX_AUTO']),
                           'pixel_scale': pixel_scale,
                           'naxis': 2,
                           'naxis1': amg_header['naxis1'],
                           'naxis2': amg_header['naxis2'],
                           'ra': amg_header['crval1'],
                           'dec': amg_header['crval2'],
                           'statistics': True,
                           }
    return catalog_payload

def read_header(fits_file):
    hdu_list = fits.open(fits_file)
    header = hdu_list[0].header
    return hdu_list, header

def find_binary(program):
    """Python equivalent of 'which' command to find a binary in the path (can
    also be given a specific pathname"""

    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

def run_sextractor(dest_dir, fits_file, binary=None):

    binary = binary or find_binary("sex")
    if binary is None:
        print("Could not locate 'sex' executable in PATH")
        return -42
    sextractor_config_file = 'sextractor_neox_ldac.conf'
    options = '-CATALOG_TYPE ASCII_HEAD -CATALOG_NAME {}'.format(fits_file.replace('.fits', '.asc'))
    cmdline = "%s %s -c %s %s" % ( binary, fits_file, sextractor_config_file, options )
    cmdline = cmdline.rstrip()
    args = cmdline.split()
    retcode_or_cmdline = call(args, cwd=dest_dir)

    return retcode_or_cmdline

def update_fits_header(image_header, response_json):
    '''Update the fits header <image_header> with results of astrometric fit from <response_json>
    The updated header is returned
    '''
    
    header_keywords_to_update = ['CTYPE1', 'CTYPE2', 'CRPIX1', 'CRPIX2', 'CRVAL1',
                                     'CRVAL2', 'CD1_1', 'CD1_2', 'CD2_1', 'CD2_2']

    for keyword in header_keywords_to_update:
        image_header[keyword] = response_json[keyword]

    if response_json['solved'] is True:
        #update wcs status, rms error, # of match sources, catalog type in header
        image_header['WCSERR'] = 0
        image_header['WCSRDRES'] = response_json['rms_error']
        image_header['WCSMATCH'] = response_json['num_source_matches']
        image_header['WCCATTYP'] = 'GAIA-DR2'

    return image_header 

def add_ra_dec_to_catalog(catalog, header):
    image_wcs = wcs.WCS(header)
    ras, decs = image_wcs.all_pix2world(catalog['XWIN_IMAGE'], catalog['YWIN_IMAGE'], 1)
    catalog['ra'] = ras
    catalog['dec'] = decs
    catalog['ra'].unit = 'degree'
    catalog['dec'].unit = 'degree'
    catalog['ra'].description = 'Right Ascension'
    catalog['dec'].description = 'Declination'

    return catalog

url =  'http://astrometry.lco.gtn/catalog/'
if __name__ == "__main__":
    #find all fits_files in destination directory
    dest_dir = os.path.join('/apophis','eng','rocks','20190723','2019_OD','target_in_field')
    fits_files = find_images(dest_dir)
    for fits_file in fits_files[0:6]:
        print(fits_file)
        #run sextractor
        catfile = fits_file.replace('.fits','.asc')
        if os.path.exists(catfile) is False:
            status = run_sextractor(dest_dir, fits_file)
        else:
            print("catalog already exists")
            status = 0
        #print("status=", status)
        #read in sextractor catalog
        image_catalog = Table.read(catfile, format='ascii.sextractor')
        hdu_list, header = read_header(fits_file)
        payload = make_payload(image_catalog, header)
        #send to astrometry service
        astrometry_response = requests.post(url, json=payload)
        if astrometry_response.status_code == 200:

            if astrometry_response.json()['solved'] is True:
                print('solved')
                #update fits header
                new_header = update_fits_header(header, astrometry_response.json())
                # Write out new file
                hdu_list[0].header = new_header
                new_file =fits_file.replace('g00', 'g91')
                hdu_list.writeto(new_file, checksum=True, overwrite=True)
        #add ra dec columns to catalog
                new_catalog = add_ra_dec_to_catalog(image_catalog, new_header)

        #write out catalog
                new_catalog_file = new_file.replace('.fits', '.ecsv')
                new_catalog.write(new_catalog_file, format='ascii.ecsv', overwrite=True)
                print("Wrote catalog to: ", new_catalog_file)




