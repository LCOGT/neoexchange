# coding: utf-8
import tempfile
temp_dir = tempfile.mkdtemp(prefix='tmp_neox_')
shutil.copy(os.path.abspath(test_photpipefilename), temp_dir)
import shutil
shutil.copy(os.path.abspath(test_photpipefilename), temp_dir)
import os
test_photpipefilename = os.path.join('photometrics', 'tests', 'photpipe_test_ldac.fits')
shutil.copy(os.path.abspath(test_photpipefilename), temp_dir)
test_photpipefilename = os.path.join(temp_dir, os.path.basename(test_photpipefilename))
test_photpipefilename
from photometrics.catalog_subs import *
header, table = extract_catalog(test_photpipefilename)
len(header)
header.keys()
sorted(header.keys())
expected_hdr = {'astrometric_catalog': 'GAIA',
               'astrometric_fit_nstars': -4,
               'astrometric_fit_rms': 0.046402414945362,
               'astrometric_fit_status': 0,
               'exptime': 124.973,
               'field_center_dec': -20.80239166666667,
               'field_center_ra': 342.1171083333333,
               'field_height': '26.5953m',
               'field_width': '26.5953m',
               'filter': 'w',
               'framename': 'lsc1m005-fa15-20220730-0319-e00.fits',
               'fwhm': 3.335374522705078,
               'instrument': 'fa15',
               'obs_date': datetime(2022, 7, 31,  3, 38,  8, 692000),
               'obs_midpoint': datetime(2022, 7, 31,  3, 39, 11, 178500),
               'pixel_scale': 0.38958,
               'site_code': 'W85',
               'reduction_level' : 91,
               'zeropoint': -99.0,
               'zeropoint_err': -99.0,
               'zeropoint_src': 'BANZAI',
               'wcs' : self.test_photpipe_ldacwcs,
               'aperture_radius_pixels' : 11.47,
               'aperture_radius_arcsec' : round(11.47*self.test_photpipe_ldac_pixscale, 4)}
test_photpipe_ldacwcs
header = fits.Header.fromtextfile(os.path.join('photometrics', 'tests', 'example_photpipe.head'))
test_photpipe_ldacwcs = WCS(header)
expected_hdr = {'astrometric_catalog': 'GAIA',
               'astrometric_fit_nstars': -4,
               'astrometric_fit_rms': 0.046402414945362,
               'astrometric_fit_status': 0,
               'exptime': 124.973,
               'field_center_dec': -20.80239166666667,
               'field_center_ra': 342.1171083333333,
               'field_height': '26.5953m',
               'field_width': '26.5953m',
               'filter': 'w',
               'framename': 'lsc1m005-fa15-20220730-0319-e00.fits',
               'fwhm': 3.335374522705078,
               'instrument': 'fa15',
               'obs_date': datetime(2022, 7, 31,  3, 38,  8, 692000),
               'obs_midpoint': datetime(2022, 7, 31,  3, 39, 11, 178500),
               'pixel_scale': 0.38958,
               'site_code': 'W85',
               'reduction_level' : 91,
               'zeropoint': -99.0,
               'zeropoint_err': -99.0,
               'zeropoint_src': 'BANZAI',
               'wcs' : test_photpipe_ldacwcs,
               'aperture_radius_pixels' : 11.47,
               'aperture_radius_arcsec' : round(11.47*self.test_photpipe_ldac_pixscale, 4)}
expected_hdr = {'astrometric_catalog': 'GAIA',
               'astrometric_fit_nstars': -4,
               'astrometric_fit_rms': 0.046402414945362,
               'astrometric_fit_status': 0,
               'exptime': 124.973,
               'field_center_dec': -20.80239166666667,
               'field_center_ra': 342.1171083333333,
               'field_height': '26.5953m',
               'field_width': '26.5953m',
               'filter': 'w',
               'framename': 'lsc1m005-fa15-20220730-0319-e00.fits',
               'fwhm': 3.335374522705078,
               'instrument': 'fa15',
               'obs_date': datetime(2022, 7, 31,  3, 38,  8, 692000),
               'obs_midpoint': datetime(2022, 7, 31,  3, 39, 11, 178500),
               'pixel_scale': 0.38958,
               'site_code': 'W85',
               'reduction_level' : 91,
               'zeropoint': -99.0,
               'zeropoint_err': -99.0,
               'zeropoint_src': 'BANZAI',
               'wcs' : test_photpipe_ldacwcs,
               'aperture_radius_pixels' : 11.47,
               'aperture_radius_arcsec' : round(11.47*test_photpipe_ldac_pixscale, 4)}
test_photpipe_ldac_pixscale = round(proj_plane_pixel_scales(test_photpipe_ldacwcs).mean()*3600.0, 5)
expected_hdr = {'astrometric_catalog': 'GAIA',
               'astrometric_fit_nstars': -4,
               'astrometric_fit_rms': 0.046402414945362,
               'astrometric_fit_status': 0,
               'exptime': 124.973,
               'field_center_dec': -20.80239166666667,
               'field_center_ra': 342.1171083333333,
               'field_height': '26.5953m',
               'field_width': '26.5953m',
               'filter': 'w',
               'framename': 'lsc1m005-fa15-20220730-0319-e00.fits',
               'fwhm': 3.335374522705078,
               'instrument': 'fa15',
               'obs_date': datetime(2022, 7, 31,  3, 38,  8, 692000),
               'obs_midpoint': datetime(2022, 7, 31,  3, 39, 11, 178500),
               'pixel_scale': 0.38958,
               'site_code': 'W85',
               'reduction_level' : 91,
               'zeropoint': -99.0,
               'zeropoint_err': -99.0,
               'zeropoint_src': 'BANZAI',
               'wcs' : test_photpipe_ldacwcs,
               'aperture_radius_pixels' : 11.47,
               'aperture_radius_arcsec' : round(11.47*test_photpipe_ldac_pixscale, 4)}
assert sorted(header.keys()) == sorted(expected_hdr.keys())
set(sorted(header.items())) ^ set(sorted(expected_hdr.items()))
header
header, table = extract_catalog(test_photpipefilename)
header
set(sorted(header.items())) ^ set(sorted(expected_hdr.items()))
header, table, cattype = open_fits_catalog(test_banzaifilename)
test_banzaifilename = os.path.join('photometrics', 'tests', 'banzai_test_frame.fits.fz')
hdulist = fits.open(test_banzaifilename)
test_banzaiheader = hdulist['SCI'].header
test_banzaitable = hdulist['CAT'].data
test_banzaiwcs = WCS(test_banzaiheader)
hdulist.close()
header, table, cattype = open_fits_catalog(test_banzaifilename)
header, table, cattype = open_fits_catalog(test_banzaifilename)
frame_header = get_catalog_header(header, "BANZAI")
obs_date = datetime.strptime('2016-06-06T22:48:14', '%Y-%m-%dT%H:%M:%S')
expected_params = { 'site_code'  : 'K92',
                    'instrument' : 'kb76',
                    'filter'     : 'w',
                    'framename'  : 'cpt1m013-kb76-20160606-0396-e00.fits',
                    'exptime'    : 100.0,
                    'obs_date'      : obs_date,
                    'obs_midpoint'  : obs_date + timedelta(seconds=100.0 / 2.0),
                    'field_center_ra'  : Angle('18:11:47.017', unit=u.hour).deg,
                    'field_center_dec' : Angle('+01:16:54.21', unit=u.deg).deg,
                    'field_width'   : '15.8715m',
                    'field_height'  : '15.9497m',
                    'pixel_scale'   : 0.46957,
                    'fwhm'          : 2.110443536975972,
                    'astrometric_fit_status' : 0,
                    'astrometric_catalog'    : '2MASS',
                    'astrometric_fit_rms'    : 0.3,
                    'astrometric_fit_nstars' : -4,
                    'zeropoint'     : -99,
                    'zeropoint_err' : -99,
                    'zeropoint_src' : 'BANZAI',
                    'wcs'           : test_banzaiwcs,
                    'reduction_level' : 91,
                    'gain'          : 1.0
                  }
set(sorted(frame_header.items())) ^ set(sorted(expected_params.items()))
expected_params = { 'site_code'  : 'K92',
                    'enc_id' : 'domb',
                    'site_id' : 'cpt',
                    'tel_id' : '1m0a',
                    'block_start' : datetime(2016, 6, 6, 22, 24, 44),
                    'block_end' : datetime(2016, 6, 6, 22, 49, 38),
                    'groupid' : 'XL8B85F_K92-20160607_ToO',
                    'object_name' : 'XL8B85F',
                    'proposal' : 'LCO2016A-021',
                    'request_number' : '0000622341',
                    'instrument' : 'kb76',
                    'filter'     : 'w',
                    'framename'  : 'cpt1m013-kb76-20160606-0396-e00.fits',
                    'exptime'    : 100.0,
                    'obs_date'      : obs_date,
                    'obs_midpoint'  : obs_date + timedelta(seconds=100.0 / 2.0),
                    'field_center_ra'  : Angle('18:11:47.017', unit=u.hour).deg,
                    'field_center_dec' : Angle('+01:16:54.21', unit=u.deg).deg,
                    'field_width'   : '15.8715m',
                    'field_height'  : '15.9497m',
                    'pixel_scale'   : 0.46957,
                    'fwhm'          : 2.110443536975972,
                    'astrometric_fit_status' : 0,
                    'astrometric_catalog'    : '2MASS',
                    'astrometric_fit_rms'    : 0.3,
                    'astrometric_fit_nstars' : -4,
                    'zeropoint'     : -99,
                    'zeropoint_err' : -99,
                    'zeropoint_src' : 'BANZAI',
                    'wcs'           : test_banzaiwcs,
                    'reduction_level' : 91,
                    'gain'          : 1.0
                  }
set(sorted(frame_header.items())) ^ set(sorted(expected_params.items()))
first_file = fits_files[0]
fits_header, dummy_table, cattype = open_fits_catalog(first_file, header_only=True)
header = get_catalog_header(fits_header, cattype)
options = { 'fitspattern' : 'fm*.????.fits'}
dataroot = '/apophis/eng/rocks/MRO/data_mrocal'
obs_date ='20230225'
object_dirs = [x[0] for x in os.walk(dataroot) if ('Didymos' in x[0] or '65803' in x[0] or 'mro_' in x[0] or obs_date in x[0][-8:]) and 'Temp_cvc' not in x[0]]
datadir
object_dirs[0]
datadir = object_dirs[0]
fits_files, fits_catalogs = determine_images_and_catalogs(None, dataroot, red_level='') # red_level must be null to pickup Swope/MRO data
from core.views import determine_images_and_catalogs
fits_files, fits_catalogs = determine_images_and_catalogs(None, dataroot, red_level='') # red_level must be null to pickup Swope/MRO data
object_dirs
dataroot
fits_files = get_fits_files(datadir, options['fitspattern'])
fits_files = get_fits_files(datadir, options['fitspattern'])
first_file = fits_files[0]
fits_header, dummy_table, cattype = open_fits_catalog(first_file, header_only=True)
header = get_catalog_header(fits_header, cattype)
header
first_file = fits_files[0]
fits_header, dummy_table, cattype = open_fits_catalog(first_file, header_only=True)
header = get_catalog_header(fits_header, cattype)
first_file = fits_files[0]
fits_header, dummy_table, cattype = open_fits_catalog(first_file, header_only=True)
header = get_catalog_header(fits_header, cattype)
header
first_file = fits_files[0]
fits_header, dummy_table, cattype = open_fits_catalog(first_file, header_only=True)
header = get_catalog_header(fits_header, cattype)
header
first_file = fits_files[0]
fits_header, dummy_table, cattype = open_fits_catalog(first_file, header_only=True)
header = get_catalog_header(fits_header, cattype)
header
first_file = fits_files[0]
fits_header, dummy_table, cattype = open_fits_catalog(first_file, header_only=True)
header = get_catalog_header(fits_header, cattype)
first_file = fits_files[0]
fits_header, dummy_table, cattype = open_fits_catalog(first_file, header_only=True)
header = get_catalog_header(fits_header, cattype)
first_file = fits_files[0]
fits_header, dummy_table, cattype = open_fits_catalog(first_file, header_only=True)
header = get_catalog_header(fits_header, cattype)
first_file = fits_files[0]
fits_header, dummy_table, cattype = open_fits_catalog(first_file, header_only=True)
header = get_catalog_header(fits_header, cattype)
fits_header['FILENAME']
datetime.strptime(fits_header['FILENAME'], 'm%y%m%d')
datetime.strptime(fits_header['FILENAME'][0:8], 'm%y%m%d')
datetime.strptime(fits_header['FILENAME'][0:7], 'm%y%m%d')
first_file = fits_files[0]
fits_header, dummy_table, cattype = open_fits_catalog(first_file, header_only=True)
header = get_catalog_header(fits_header, cattype)
first_file = fits_files[0]
fits_header, dummy_table, cattype = open_fits_catalog(first_file, header_only=True)
header = get_catalog_header(fits_header, cattype)
header
first_file = fits_files[0]
fits_header, dummy_table, cattype = open_fits_catalog(first_file, header_only=True)
header = get_catalog_header(fits_header, cattype)
header
dark_start, dark_end = determine_darkness_times('H01', obs_night, sun_zd=90.5)
obs_night datetime.strptime(fits_header['FILENAME'][0:7], 'm%y%m%d')
obs_night = datetime.strptime(fits_header['FILENAME'][0:7], 'm%y%m%d')
obs_night
dark_start, dark_end = determine_darkness_times('H01', obs_night, sun_zd=90.5)
get_sitepos(sitecode)
from astrometrics.ephem_subs import get_sitepos
get_sitepos(sitecode)
sitecode='H01'
get_sitepos(sitecode)
import pyslalib.slalib as S
S.sla_obs("?")
get_ipython().run_line_magic('pinfo', 'S.sla_obs')
S.sla_obs(-01,'?')
S.sla_obs(-1,'?')
get_sitepos(sitecode)
dark_start, dark_end = determine_darkness_times('H01', obs_night, sun_zd=90.5)
dark_start
first_file = fits_files[0]
fits_header, dummy_table, cattype = open_fits_catalog(first_file, header_only=True)
header = get_catalog_header(fits_header, cattype)
header
header, table, cattype = open_fits_catalog(self.test_swopefilename)
header, table, cattype = open_fits_catalog(test_swopefilename)
test_swopefilename = os.path.join('photometrics', 'tests', 'swope_test_frame.fits')
hdulist = fits.open(test_swopefilename)
test_swopeheader = hdulist[0].header
hdulist.close()
WCS(test_swopeheader)
swope_wcs = WCS(test_swopeheader)
proj_plane_pixel_scales(swope_wcs)
proj_plane_pixel_scales(swope_wcs)*3600
test_swopeldacfilename = os.path.join('photometrics', 'tests', 'swope_test_ldac.fits')
hdulist = fits.open(test_swopeldacfilename)
header_array = hdulist[1].data[0][0]
swope_ldac_header = fits_ldac_to_header(header_array)
test_swope_ldacwcs = WCS(header)
test_swope_ldac_pixscale = round(proj_plane_pixel_scales(test_swope_ldacwcs).mean()*3600.0, 5)
test_swope_ldactable = hdulist[2].data
hdulist.close()
header, table, cattype = open_fits_catalog(test_swopefilename)
header
fits_wcs = WCS(header)
fits_wcs
fits_wcs.is_celestial
pixscale = proj_plane_pixel_scales(fits_wcs).mean()
pixscale
fits_wcs.cd
fits_wcs.pc
fits_wcs.wcs.pc
fits_wcs.wcs.cd
hasattr(fits_wcs.wcs.cd)
hasattr(fits_wcs.wcs)
get_ipython().run_line_magic('pinfo', 'hasattr')
hasattr(fits_wcs.wcs, cd)
hasattr(fits_wcs.wcs, 'cd')
hasattr(fits_wcs.wcs, 'pc')
frame_header
header
swope_frame_header = get_catalog_header(header, cattype)
swope_frame_header
get_ipython().run_line_magic('history', '')
set(sorted(swope_frame_header.items())) ^ set(sorted(expected_params.items()))
obs_date = datetime.strptime('2022-09-25T03:26:46.0', '%Y-%m-%dT%H:%M:%S.%f')
expected_params = { 'site_code'  : '304',
                    'tel_id'     : 'Swope',
                    'instrument' : 'D4K4',
                    'filter'     : 'r',
                    'framename'  : 'ccd1100c1',
                    'exptime'    : 10.0,
                    'obs_date'      : obs_date,
                    'obs_midpoint'  : obs_date + timedelta(seconds=10.0 / 2.0),
                    'object_name'   : 'Didymos',
                    'proposal'      : 'SWOPE2022',
                    'block_start' : datetime(2022, 9, 24, 22, 30, 0),
                    'block_end' : datetime(2022, 9, 25, 10, 30, 0),
                    'groupid' : '24Sep2022',
                    'request_number' : '24092022',
                    'tracking_number' : '24092022',
                    'field_center_ra'  : Angle('03:02:30.1', unit=u.hour).deg,
                    'field_center_dec' : Angle('-34:23:35.90', unit=u.deg).deg,
                    'field_width'   : '0.0725m',
                    'field_height'  : '0.0725m',
                    'pixel_scale'   : 0.435,
                    'wcs' : test_swope_wcs,
                    'fwhm'          : -99,
                    'astrometric_fit_status' : -99,
                    'astrometric_catalog'    : '2MASS',
                    'astrometric_fit_rms'    : 0.3,
                    'astrometric_fit_nstars' : -4,
                    'zeropoint'     : -99,
                    'zeropoint_err' : -99,
                    'zeropoint_src' : 'N/A',
                    'reduction_level' : 71
                  }
test_swopeheader
test_swope_wcs = WCS(test_swopeheader)
obs_date = datetime.strptime('2022-09-25T03:26:46.0', '%Y-%m-%dT%H:%M:%S.%f')
expected_params = { 'site_code'  : '304',
                    'tel_id'     : 'Swope',
                    'instrument' : 'D4K4',
                    'filter'     : 'r',
                    'framename'  : 'ccd1100c1',
                    'exptime'    : 10.0,
                    'obs_date'      : obs_date,
                    'obs_midpoint'  : obs_date + timedelta(seconds=10.0 / 2.0),
                    'object_name'   : 'Didymos',
                    'proposal'      : 'SWOPE2022',
                    'block_start' : datetime(2022, 9, 24, 22, 30, 0),
                    'block_end' : datetime(2022, 9, 25, 10, 30, 0),
                    'groupid' : '24Sep2022',
                    'request_number' : '24092022',
                    'tracking_number' : '24092022',
                    'field_center_ra'  : Angle('03:02:30.1', unit=u.hour).deg,
                    'field_center_dec' : Angle('-34:23:35.90', unit=u.deg).deg,
                    'field_width'   : '0.0725m',
                    'field_height'  : '0.0725m',
                    'pixel_scale'   : 0.435,
                    'wcs' : test_swope_wcs,
                    'fwhm'          : -99,
                    'astrometric_fit_status' : -99,
                    'astrometric_catalog'    : '2MASS',
                    'astrometric_fit_rms'    : 0.3,
                    'astrometric_fit_nstars' : -4,
                    'zeropoint'     : -99,
                    'zeropoint_err' : -99,
                    'zeropoint_src' : 'N/A',
                    'reduction_level' : 71
                  }
set(sorted(swope_frame_header.items())) ^ set(sorted(expected_params.items()))
set(sorted(swope_frame_header.items())) ^ set(sorted(expected_params.items()))
expected_params = { 'site_code'  : '304',
                    'site_id'    : 'LCO',   # Las Campanas, not us...
                    'tel_id'     : 'Swope',
                    'instrument' : 'D4K4',
                    'filter'     : 'r',
                    'framename'  : 'ccd1100c1',
                    'exptime'    : 10.0,
                    'num_exposures' : 200,
                    'obs_date'      : obs_date,
                    'obs_midpoint'  : obs_date + timedelta(seconds=10.0 / 2.0),
                    'object_name'   : 'Didymos',
                    'proposal'      : 'SWOPE2022',
                    'block_start' : datetime(2022, 9, 24, 22, 30, 0),
                    'block_end' : datetime(2022, 9, 25, 10, 30, 0),
                    'groupid' : '24Sep2022',
                    'request_number' : '24092022',
                    'tracking_number' : '24092022',
                    'field_center_ra'  : Angle('03:02:30.1', unit=u.hour).deg,
                    'field_center_dec' : Angle('-34:23:35.90', unit=u.deg).deg,
                    'field_width'   : '0.0725m',
                    'field_height'  : '0.0725m',
                    'pixel_scale'   : 0.435,
                    'wcs' : test_swope_wcs,
                    'fwhm'          : -99,
                    'astrometric_fit_status' : -99,
                    'astrometric_catalog'    : '2MASS',
                    'astrometric_fit_rms'    : 0.3,
                    'astrometric_fit_nstars' : -4,
                    'zeropoint'     : -99,
                    'zeropoint_err' : -99,
                    'zeropoint_src' : 'N/A',
                    'reduction_level' : 71
                  }
set(sorted(swope_frame_header.items())) ^ set(sorted(expected_params.items()))
header, table, cattype = open_fits_catalog(test_ldacfilename)
test_ldacfilename = os.path.join('photometrics', 'tests', 'ldac_test_catalog.fits')
header, table, cattype = open_fits_catalog(test_ldacfilename)
cattype
header_items = get_catalog_header(header, cattype)
header_items
catalog_items = get_catalog_items_old(header_items, self.ldac_table_firstitem, "FITS_LDAC")
catalog_items = get_catalog_items_old(header_items, ldac_table_firstitem, "FITS_LDAC")
ldac_table_firstitem = test_ldactable[0:1]
test_ldacfilename = os.path.join('photometrics', 'tests', 'ldac_test_catalog.fits')
hdulist = fits.open(test_ldacfilename)
header_array = hdulist[1].data[0][0]
header = fits_ldac_to_header(header_array)
test_ldacwcs = WCS(header)
test_ldac_pixscale = round(proj_plane_pixel_scales(test_ldacwcs).mean()*3600.0, 5)
test_ldactable = hdulist[2].data
hdulist.close()
ldac_table_firstitem = test_ldactable[0:1]
test_ldactable
catalog_items = get_catalog_items_old(header_items, ldac_table_firstitem, "FITS_LDAC")
catalog_items = get_catalog_items_new(header_items, ldac_table_firstitem, "FITS_LDAC")
get_ipython().run_line_magic('history', '')
object_dirs
first_file = fits_files[0]
fits_header, dummy_table, cattype = open_fits_catalog(first_file, header_only=True)
header = get_catalog_header(fits_header, cattype)
header
header.get('tracking_number', None)
tracking_num = header.get('tracking_number', None)
tracking_num_nopad = tracking_num.lstrip('0')
sblocks = SuperBlock.objects.filter(Q(tracking_number=tracking_num)|Q(tracking_number=tracking_num_nopad))
from core.models import Body, SuperBlock, Block, Frame, CatalogSources, SourceMeasurement, Proposal
from core.views import determine_images_and_catalogs, compare_NEOx_horizons_ephems, find_matching_image_file, run_sextractor_make_catalog, \
    run_scamp, find_block_for_frame, make_new_catalog_entry

from astrometrics.ephem_subs import horizons_ephem, compute_ephem
from photometrics.catalog_subs import *
from photometrics.external_codes import *
from matplotlib.dates import HourLocator, DateFormatter
import astropy.units as u
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from django.conf import settings
from django.db import close_old_connections
try:
    from dramatiq import pipeline

    from core.tasks import run_pipeline, send_task
    from core.models import PipelineProcess
except ImportError:
    pass
from core.frames import block_status
try:
    from summarize_obs import summarize_observations
except ImportError:
    pass
from photometrics.pds_subs import *
sblocks = SuperBlock.objects.filter(Q(tracking_number=tracking_num)|Q(tracking_number=tracking_num_nopad))
from django.db.models import Q
sblocks = SuperBlock.objects.filter(Q(tracking_number=tracking_num)|Q(tracking_number=tracking_num_nopad))
sblocks
options
block.last
Block.last()
Block.objectslast()
Block.objects.last()
block = Block.objects.last()
Frame.objects.filter(block=block)
Frame.objects.filter(block=block).frametype
Frame.objects.filter(block=block).values_list('frametype')
Frame.objects.filter(block=block).delete()
Block.objects.get(request_number=22112022)
new_block = Block.objects.get(request_number=22112022)
new_block.__dict__
new_block.id
datapath='/apophis/eng/rocks/MRO/data_mrocal/mro_221122'
block = new_block
tracking_num = block.superblock.tracking_number
obj_name = block.current_name()
if block.site.lower() in NONLCO_SITES and datapath is not None:

        data = { 'requests' : [{'id' : block.request_number,
                            'configurations' : [{'instrument_configs' : [{'exposure_count' : 1}],
                                                 'type' : 'REPEAT_EXPOSE'}
                                               ]
                          } ]
            }
        
from core.models.blocks import NONLCO_SITES
if block.site.lower() in NONLCO_SITES and datapath is not None:

        data = { 'requests' : [{'id' : block.request_number,
                            'configurations' : [{'instrument_configs' : [{'exposure_count' : 1}],
                                                 'type' : 'REPEAT_EXPOSE'}
                                               ]
                          } ]
            }
        
data
datapath
catfile = '/data/eng/rocks/MRO/data_mrocal/mro_230225/Temp_cvc/fm230225.0001-e61_ldac.fits'
 
fits_header, junk_table, cattype = open_fits_catalog(catfile, header_only=True)
cattype
header = get_catalog_header(fits_header, cattype)
fits_header
catalog_header = fits_header
fixed_values_map = {'<WCCATTYP>'  : '2MASS',  # Hardwire catalog to 2MASS for BANZAI's astrometry.net-based solves
                                              # (but could be modified based on version number further down)
                    '<ZP>'        : -99,      # Hardwire zeropoint to -99.0 for BANZAI catalogs
                    '<ZPSRC>'     : 'N/A',    # Hardwire zeropoint src to 'N/A' for BANZAI catalogs
                    '<L1ZP>'      : -99,      # Hardwire zeropoint to -99.0 for newer BANZAI catalogs where it's missing e.g. w band
                    '<L1ZPERR>'   : -99,      # Hardwire zeropoint to -99.0 for newer BANZAI catalogs where it's missing e.g. w band
                    '<L1ZPSRC>'   : 'BANZAI', # Hardwire zeropoint src to 'N/A' for newer BANZAI catalogs where it's missing
                    '<WCSRDRES>'  : 0.3,      # Hardwire RMS to 0.3"
                    '<WCSMATCH>'  : -4,       # Hardwire no. of stars matched to 4 (1 quad)
                    '<RLEVEL>'    : 91,       # Hardwire reduction level (mostly old catalogs in the tests)
                    '<L1FWHM>'    : -99,      # May not be present if BANZAI WCS fit fails
                    '<ASTRRMSx>'  : -99.0,    # Astrometric fit rms for PHOTPIPE_LDAC types if we can't convert the 2 headers
                    '<ASTIRMSx>'  : 4,        # (bad) Astrometric fit status for PHOTPIPE_LDAC types if we can't convert the 2 headers
                    '<PROPID>'    : 'SWOPE2022', # Default proposal for Swope data (which has no proposal info in the header)
                    '<SITECODE>'  : '304'
                   }
catalog_type.startswith('MRO')
catalog_type = cattype
hdr_mapping, tbl_mapping, fixed_values_map = mro_ldac_catalog_mapping(fixed_values_map)
for item in hdr_mapping.keys():
    fits_keyword = <redacted>
    if fits_keyword in catalog_header:
        # Found, extract value
        value = catalog_header[fits_keyword]
        if value == 'UNKNOWN':
            if debug:
                logger.debug('UNKNOWN value found for %s', fits_keyword)
            raise FITSHdrException(fits_keyword)
        # Convert if necessary
        if item != 'field_width' and item != 'field_height':
            new_value = convert_value(item, value)
        else:
            new_value = value
        header_item = { item: new_value}
        header_items.update(header_item)
    elif fits_keyword[0] == '<' and fits_keyword[-1] == '>':
        header_item = None
        if fits_keyword =<redacted>
            # Suppress warnings from newer astropy versions which raise
            # FITSFixedWarning on the lack of OBSGEO-L,-B,-H keywords even
            # though we have OBSGEO-X,-Y,-Z as recommended by the FITS
            # Paper VII standard...
            warnings.simplefilter('ignore', category=FITSFixedWarning)
            try:
                fits_wcs = WCS(catalog_header)
            except InvalidTransformError:
                raise NeoException('Invalid WCS solution')
            pixscale = proj_plane_pixel_scales(fits_wcs).mean()
            # Only multiply by 3600 (deg->arcsec) if it's actually a celestial WCS
            if fits_wcs.is_celestial:
                pixscale *= 3600.0
            else:
                if 'xbinning' in hdr_mapping and 'PIXSCALE' in fixed_values_map:
                    pixscale = fixed_values_map['PIXSCALE'] * catalog_header[hdr_mapping['xbinning']]
                    # Delete from map to prevent incorrect values being put in later
                    del fixed_values_map['PIXSCALE']
            header_item = {item: round(pixscale, 5), 'wcs' : fits_wcs}
        # See if there is a version of the keyword in the file first
        file_fits_keyword = <redacted>
        if catalog_header.get(file_fits_keyword, None) is not None:
            value = catalog_header[file_fits_keyword]
            # Convert if necessary
            if item != 'field_width' and item != 'field_height' and item != 'aperture_radius_arcsec':
                new_value = convert_value(item, value)
            else:
                new_value = value
            header_item = { item: new_value}
        else:
            print("Fixed mapping")
                
for item in hdr_mapping.keys():
    fits_keyword = <redacted>
    print(fits_keyword)
    if fits_keyword in catalog_header:
        # Found, extract value
        value = catalog_header[fits_keyword]
        if value == 'UNKNOWN':
            if debug:
                logger.debug('UNKNOWN value found for %s', fits_keyword)
            raise FITSHdrException(fits_keyword)
        # Convert if necessary
        if item != 'field_width' and item != 'field_height':
            new_value = convert_value(item, value)
        else:
            new_value = value
        header_item = { item: new_value}
        header_items.update(header_item)
    elif fits_keyword[0] == '<' and fits_keyword[-1] == '>':
        header_item = None
        if fits_keyword =<redacted>
            # Suppress warnings from newer astropy versions which raise
            # FITSFixedWarning on the lack of OBSGEO-L,-B,-H keywords even
            # though we have OBSGEO-X,-Y,-Z as recommended by the FITS
            # Paper VII standard...
            warnings.simplefilter('ignore', category=FITSFixedWarning)
            try:
                fits_wcs = WCS(catalog_header)
            except InvalidTransformError:
                raise NeoException('Invalid WCS solution')
            pixscale = proj_plane_pixel_scales(fits_wcs).mean()
            # Only multiply by 3600 (deg->arcsec) if it's actually a celestial WCS
            if fits_wcs.is_celestial:
                pixscale *= 3600.0
            else:
                if 'xbinning' in hdr_mapping and 'PIXSCALE' in fixed_values_map:
                    pixscale = fixed_values_map['PIXSCALE'] * catalog_header[hdr_mapping['xbinning']]
                    # Delete from map to prevent incorrect values being put in later
                    del fixed_values_map['PIXSCALE']
            header_item = {item: round(pixscale, 5), 'wcs' : fits_wcs}
        # See if there is a version of the keyword in the file first
        file_fits_keyword = <redacted>
        if catalog_header.get(file_fits_keyword, None) is not None:
            value = catalog_header[file_fits_keyword]
            # Convert if necessary
            if item != 'field_width' and item != 'field_height' and item != 'aperture_radius_arcsec':
                new_value = convert_value(item, value)
            else:
                new_value = value
            header_item = { item: new_value}
        else:
            print("Fixed mapping", fits_keyword, fixed_values_map[fits_keyword])
                
for item in hdr_mapping.keys():
    fits_keyword = <redacted>
    print(fits_keyword)
    if fits_keyword in catalog_header:
        # Found, extract value
        value = catalog_header[fits_keyword]
        if value == 'UNKNOWN':
            if debug:
                logger.debug('UNKNOWN value found for %s', fits_keyword)
            raise FITSHdrException(fits_keyword)
        # Convert if necessary
        if item != 'field_width' and item != 'field_height':
            new_value = convert_value(item, value)
        else:
            new_value = value
        header_item = { item: new_value}
        header_items.update(header_item)
    elif fits_keyword[0] == '<' and fits_keyword[-1] == '>':
        header_item = None
        if fits_keyword =<redacted>
            # Suppress warnings from newer astropy versions which raise
            # FITSFixedWarning on the lack of OBSGEO-L,-B,-H keywords even
            # though we have OBSGEO-X,-Y,-Z as recommended by the FITS
            # Paper VII standard...
            warnings.simplefilter('ignore', category=FITSFixedWarning)
            try:
                fits_wcs = WCS(catalog_header)
            except InvalidTransformError:
                raise NeoException('Invalid WCS solution')
            pixscale = proj_plane_pixel_scales(fits_wcs).mean()
            # Only multiply by 3600 (deg->arcsec) if it's actually a celestial WCS
            if fits_wcs.is_celestial:
                pixscale *= 3600.0
            else:
                if 'xbinning' in hdr_mapping and 'PIXSCALE' in fixed_values_map:
                    pixscale = fixed_values_map['PIXSCALE'] * catalog_header[hdr_mapping['xbinning']]
                    # Delete from map to prevent incorrect values being put in later
                    del fixed_values_map['PIXSCALE']
            header_item = {item: round(pixscale, 5), 'wcs' : fits_wcs}
        # See if there is a version of the keyword in the file first
        file_fits_keyword = <redacted>
        if catalog_header.get(file_fits_keyword, None) is not None:
            value = catalog_header[file_fits_keyword]
            # Convert if necessary
            if item != 'field_width' and item != 'field_height' and item != 'aperture_radius_arcsec':
                new_value = convert_value(item, value)
            else:
                new_value = value
            header_item = { item: new_value}
        else:
            print("Fixed mapping", fits_keyword, fixed_values_map.get(fits_keyword, 'XXX'))
        
                
warnings.simplefilter('ignore', category=FITSFixedWarning)
try:
    fits_wcs = WCS(catalog_header)
except InvalidTransformError:
    raise NeoException('Invalid WCS solution')
    
fits_wcs
pixscale = proj_plane_pixel_scales(fits_wcs).mean()
pixscale
if fits_wcs.is_celestial:
    pixscale *= 3600.0
    
pixscale
'xbinning' in hdr_mapping and 'PIXSCALE' in fixed_values_map
pixscale = fixed_values_map['PIXSCALE'] * catalog_header[hdr_mapping['xbinning']]
fixed_values_map['PIXSCALE'] , catalog_header[hdr_mapping['xbinning']]
fits_header
hdulist = fits.open('photometrics/tests/photpipe_test_ldac.fits')
hdulist.info()
len(hdulist) == 3 and hdulist[1].header.get('EXTNAME', None) == 'LDAC_IMHEAD'
header_array = hdulist[1].data[0][0]
header_array
hdulist_mro = fits.open('/apophis/eng/rocks/MRO/data_mrocal/mro_230225/fm230225.0001_ldac-e61.fits')
header_array_mro = hdulist_mro[1].data[0][0]
header_array
header_array_mro
len(header_array_mro)
i=0
i=0
while i < len(header_array)-1:
    card = header_array[i]
    keyword = <redacted>
    if len(card.strip()) != 0:
        if keyword.rstrip() == "COMMENT":
            comment_text = card[8:]
            header.add_comment(comment_text)
        elif keyword.rstrip() != "HISTORY":
            comment_loc = card.rfind('/ ')
            if comment_loc == -1:
                comment_loc = len(card)
            value = card[10:comment_loc]
            print(f"{i>3d}: {keyword} {value} {type(value)}")
i=0
while i < len(header_array)-1:
    card = header_array[i]
    keyword = <redacted>
    if len(card.strip()) != 0:
        if keyword.rstrip() == "COMMENT":
            comment_text = card[8:]
            header.add_comment(comment_text)
        elif keyword.rstrip() != "HISTORY":
            comment_loc = card.rfind('/ ')
            if comment_loc == -1:
                comment_loc = len(card)
            value = card[10:comment_loc]
            print(f"{i:>3d}: {keyword} {value} {type(value)}")
            
i=0
while i < len(header_array)-1:
    card = header_array[i]
    keyword = <redacted>
    if len(card.strip()) != 0:
        if keyword.rstrip() == "COMMENT":
            comment_text = card[8:]
            header.add_comment(comment_text)
        elif keyword.rstrip() != "HISTORY":
            comment_loc = card.rfind('/ ')
            if comment_loc == -1:
                comment_loc = len(card)
            value = card[10:comment_loc]
            print(f"{i:>3d}: {keyword} {value} {type(value)}")
    i += 1
     
header = fits.Header()
i=0
while i < len(header_array)-1:
    card = header_array[i]
    keyword = <redacted>
    if len(card.strip()) != 0:
        if keyword.rstrip() == "COMMENT":
            comment_text = card[8:]
            header.add_comment(comment_text)
        elif keyword.rstrip() != "HISTORY":
            comment_loc = card.rfind('/ ')
            if comment_loc == -1:
                comment_loc = len(card)
            value = card[10:comment_loc]
            print(f"{i:>3d}: {keyword} {value} {type(value)}")
    i += 1
     
header = fits.Header()
i=0
while i < len(header_array_mro)-1:
    card = header_array_mro[i]
    keyword = <redacted>
    if len(card.strip()) != 0:
        if keyword.rstrip() == "COMMENT":
            comment_text = card[8:]
            header.add_comment(comment_text)
        elif keyword.rstrip() != "HISTORY":
            comment_loc = card.rfind('/ ')
            if comment_loc == -1:
                comment_loc = len(card)
            value = card[10:comment_loc]
            print(f"{i:>3d}: {keyword} {value} {type(value)}")
    i += 1
     
header_array_mro
header = fits.Header()
i=0
while i < len(header_array_mro)-1:
    card = header_array_mro[i]
    keyword = <redacted>
    if len(card.strip()) != 0:
        if keyword.rstrip() == "COMMENT":
            comment_text = card[8:]
            header.add_comment(comment_text)
        elif keyword.rstrip() != "HISTORY":
            comment_loc = card.rfind(' /')
            if comment_loc == -1:
                comment_loc = len(card)
            value = card[10:comment_loc]
            print(f"{i:>3d}: {keyword} {value} {type(value)}")
    i += 1
     
git diff
get_ipython().system('git diff')
header_array_mro
fits_ldac_to_header(header_array_mro)
fits_ldac_to_header(header_array_mro)
fits_ldac_to_header(header_array_mro)
fits_ldac_to_header(header_array_mro)
header = fits_ldac_to_header(header_array_mro)
header['BITPIX']
header.comments
header.values()
for foo in header.items():
    print(foo)
    
header.comments['BITPIX']
header.comments['BITPIX']
float('1.03149 ')
value = "'1.03149 '         "
float(value)
float(str(value))
fits_ldac_to_header(header_array_mro)
get_ipython().run_line_magic('history', '')
fits_header
fits_header, junk_table, cattype = open_fits_catalog(catfile, header_only=True)
print(cattype)
header = get_catalog_header(fits_header, cattype)
header
shutil.copy(os.path.abspath(test_ldacfilename), temp_dir)
test_ldacfilename = os.path.join(temp_dir, os.path.basename(test_ldacfilename))
test_ldacfilename
header, table = extract_catalog(test_ldacfilename)
set(sorted(header.items())) ^ set(sorted(expected_hdr.items()))
expected_hdr = {'astrometric_catalog': 'UCAC4',
               'astrometric_fit_nstars': 22,
               'astrometric_fit_rms': 0.14473999999999998,
               'astrometric_fit_status': 0,
               'exptime': 115.0,
               'field_center_dec': -9.767727777777779,
               'field_center_ra': 219.83084166666666,
               'field_height': '15.9562m',
               'field_width': '15.8779m',
               'filter': 'w',
               'framename': 'cpt1m013-kb76-20160428-0141-e00.fits',
               'fwhm': 2.886,
               'instrument': 'kb76',
               'obs_date': datetime(2016, 4, 28, 20, 11, 54, 303000),
               'obs_midpoint': datetime(2016, 4, 28, 20, 12, 51, 803000),
               'pixel_scale': 0.46976,
               'site_code': 'K92',
               'reduction_level' : 91,
               'zeropoint': -99.0,
               'zeropoint_err': -99.0,
               'zeropoint_src': 'NOT_FIT(LCOGTCAL-V0.0.2-r8174)',
               'wcs' : test_ldacwcs,
               'aperture_radius_pixels' : 2.5,
               'aperture_radius_arcsec' : round(2.5*test_ldac_pixscale, 4)}
set(sorted(header.items())) ^ set(sorted(expected_hdr.items()))
options = {'tempdir' : 'Temp_cvc_multiap', 'refcat' : 'GAIA-DR2', 'zp_tolerance' : 0.1, 'overwrite' : False, 'color_const' : True, 'solar' : False}
catalog_type = 'FITS_LDAC_MULTIAPER'
file_index = fits_files.index(os.path.join(dataroot, 'fm230225.0040-e61.fits'))
fits_filepath = fits_files[file_index]
fits_file = os.path.basename(fits_filepath)
origin = 'LCO'
if 'rccd' in fits_file:
    origin = 'SWOPE'
elif 'fm2' in fits_files[0]:
    origin = 'MRO'
mapping = file_mapping(origin)
steps = [{
            'name'   : 'proc-extract',
            'inputs' : {'fits_file':fits_filepath,
                       'datadir': os.path.join(dataroot, options['tempdir']),
                       'overwrite' : options['overwrite'],
                       'catalog_type' : catalog_type}
        },
        {
            'name'   : 'proc-astromfit',
            'inputs' : {'fits_file' : fits_filepath,
                        'ldac_catalog' : os.path.join(dataroot, options['tempdir'], fits_file.replace(mapping['proc-astromfit'][0], mapping['proc-astromfit'][1])),
                        'datadir' : os.path.join(dataroot, options['tempdir'])
                        }
        },
        {
            'name'   : 'proc-extract',
            'inputs' : {'fits_file': os.path.join(dataroot, options['tempdir'], fits_file.replace(mapping['proc-extract'][0], mapping['proc-extract'][1])),
                       'datadir': os.path.join(dataroot, options['tempdir']),
                       'overwrite' : options['overwrite'],
                       'catalog_type' : catalog_type}
        },
        {
            'name'   : 'proc-zeropoint',
            'inputs' : {'ldac_catalog' : os.path.join(dataroot, options['tempdir'], fits_file.replace(mapping['proc-zeropoint'][0], mapping['proc-zeropoint'][1])),
                        'datadir' : os.path.join(dataroot, options['tempdir']),
                        'zeropoint_tolerance' : options['zp_tolerance'],
                        'catalog_type' :  mapping['final_catalog_type'],
                        'desired_catalog' : options['refcat'],
                        'color_const' : options['color_const'],
                        'solar' : options['solar']
                        }
        }]
print(f"Running pipeline on {fits_file}, producing {catalog_type} catalogs :")
dataroot
dataroot = os.path.join(dataroot, 'mro_230225')
fits_files, fits_catalogs = determine_images_and_catalogs(self, dataroot, red_level='') # red_level must be null to pickup Swope/MRO data
self=None
fits_files, fits_catalogs = determine_images_and_catalogs(self, dataroot, red_level='') # red_level must be null to pickup Swope/MRO data
options = {'tempdir' : 'Temp_cvc_multiap', 'refcat' : 'GAIA-DR2', 'zp_tolerance' : 0.1, 'overwrite' : False, 'color_const' : True, 'solar' : False}
catalog_type = 'FITS_LDAC_MULTIAPER'
file_index = fits_files.index(os.path.join(dataroot, 'fm230225.0040-e61.fits'))
fits_filepath = fits_files[file_index]
fits_file = os.path.basename(fits_filepath)
origin = 'LCO'
if 'rccd' in fits_file:
    origin = 'SWOPE'
elif 'fm2' in fits_files[0]:
    origin = 'MRO'
mapping = file_mapping(origin)
steps = [{
            'name'   : 'proc-extract',
            'inputs' : {'fits_file':fits_filepath,
                       'datadir': os.path.join(dataroot, options['tempdir']),
                       'overwrite' : options['overwrite'],
                       'catalog_type' : catalog_type}
        },
        {
            'name'   : 'proc-astromfit',
            'inputs' : {'fits_file' : fits_filepath,
                        'ldac_catalog' : os.path.join(dataroot, options['tempdir'], fits_file.replace(mapping['proc-astromfit'][0], mapping['proc-astromfit'][1])),
                        'datadir' : os.path.join(dataroot, options['tempdir'])
                        }
        },
        {
            'name'   : 'proc-extract',
            'inputs' : {'fits_file': os.path.join(dataroot, options['tempdir'], fits_file.replace(mapping['proc-extract'][0], mapping['proc-extract'][1])),
                       'datadir': os.path.join(dataroot, options['tempdir']),
                       'overwrite' : options['overwrite'],
                       'catalog_type' : catalog_type}
        },
        {
            'name'   : 'proc-zeropoint',
            'inputs' : {'ldac_catalog' : os.path.join(dataroot, options['tempdir'], fits_file.replace(mapping['proc-zeropoint'][0], mapping['proc-zeropoint'][1])),
                        'datadir' : os.path.join(dataroot, options['tempdir']),
                        'zeropoint_tolerance' : options['zp_tolerance'],
                        'catalog_type' :  mapping['final_catalog_type'],
                        'desired_catalog' : options['refcat'],
                        'color_const' : options['color_const'],
                        'solar' : options['solar']
                        }
        }]
print(f"Running pipeline on {fits_file}, producing {catalog_type} catalogs :")
get_ipython().run_line_magic('cpaste', '')
def file_mapping(origin='LCO'):
    mapping = {'LCO' : { 'proc-astromfit' : ('e91.fits', 'e91_ldac.fits'),
                         'proc-extract' : ('e91.fits', 'e92.fits'),
                         'proc-zeropoint' : ('e91.fits', 'e92_ldac.fits'),
                         'final_catalog_type' : 'BANZAI_LDAC'
                       },
               'SWOPE' : { 'proc-astromfit' : ('.fits', '_ldac.fits'),
                           'proc-extract' : ('.fits', '-e72.fits'),
                           'proc-zeropoint' : ('.fits', '-e72_ldac.fits'),
                           'final_catalog_type' : 'SWOPE_LDAC'
                       },
               'MRO'  : { 'proc-astromfit' : ('e61.fits', 'e61_ldac.fits'),
                          'proc-extract' : ('e61.fits', 'e62.fits'),
                          'proc-zeropoint' : ('e91.fits', 'e62_ldac.fits'),
                          'final_catalog_type' : 'MRO_LDAC'
                       },
              }
    return mapping[origin]
options = {'tempdir' : 'Temp_cvc_multiap', 'refcat' : 'GAIA-DR2', 'zp_tolerance' : 0.1, 'overwrite' : False, 'color_const' : True, 'solar' : False}
catalog_type = 'FITS_LDAC_MULTIAPER'
file_index = fits_files.index(os.path.join(dataroot, 'fm230225.0040-e61.fits'))
fits_filepath = fits_files[file_index]
fits_file = os.path.basename(fits_filepath)
origin = 'LCO'
if 'rccd' in fits_file:
    origin = 'SWOPE'
elif 'fm2' in fits_files[0]:
    origin = 'MRO'
mapping = file_mapping(origin)
steps = [{
            'name'   : 'proc-extract',
            'inputs' : {'fits_file':fits_filepath,
                       'datadir': os.path.join(dataroot, options['tempdir']),
                       'overwrite' : options['overwrite'],
                       'catalog_type' : catalog_type}
        },
        {
            'name'   : 'proc-astromfit',
            'inputs' : {'fits_file' : fits_filepath,
                        'ldac_catalog' : os.path.join(dataroot, options['tempdir'], fits_file.replace(mapping['proc-astromfit'][0], mapping['proc-astromfit'][1])),
                        'datadir' : os.path.join(dataroot, options['tempdir'])
                        }
        },
        {
            'name'   : 'proc-extract',
            'inputs' : {'fits_file': os.path.join(dataroot, options['tempdir'], fits_file.replace(mapping['proc-extract'][0], mapping['proc-extract'][1])),
                       'datadir': os.path.join(dataroot, options['tempdir']),
                       'overwrite' : options['overwrite'],
                       'catalog_type' : catalog_type}
        },
        {
            'name'   : 'proc-zeropoint',
            'inputs' : {'ldac_catalog' : os.path.join(dataroot, options['tempdir'], fits_file.replace(mapping['proc-zeropoint'][0], mapping['proc-zeropoint'][1])),
                        'datadir' : os.path.join(dataroot, options['tempdir']),
                        'zeropoint_tolerance' : options['zp_tolerance'],
                        'catalog_type' :  mapping['final_catalog_type'],
                        'desired_catalog' : options['refcat'],
                        'color_const' : options['color_const'],
                        'solar' : options['solar']
                        }
        }]
print(f"Running pipeline on {fits_file}, producing {catalog_type} catalogs :")
pipes = []
for step in steps[0:1]:
    pipeline_cls = PipelineProcess.get_subclass(step['name'])
    inputs = {f: pipeline_cls.inputs[f]['default'] for f in pipeline_cls.inputs}
    inputs.update(step['inputs'])
    print(f"  Performing pipeline step {step['name']}")
    pipe = pipeline_cls.create_timestamped(inputs)
#                self.stdout.write(f"  PK={pipe.pk} for {step['name']}")
    pipes.append(run_pipeline.message_with_options(args=[pipe.pk, step['name']], pipe_ignore=True))
runner  = pipeline(pipes).run()
close_old_connections()
pipes = []
for step in steps[0:1]:
    pipeline_cls = PipelineProcess.get_subclass(step['name'])
    inputs = {f: pipeline_cls.inputs[f]['default'] for f in pipeline_cls.inputs}
    inputs.update(step['inputs'])
    print(f"  Performing pipeline step {step['name']}")
    pipe = pipeline_cls.create_timestamped(inputs)
#                self.stdout.write(f"  PK={pipe.pk} for {step['name']}")
    pipes.append(run_pipeline.message_with_options(args=[pipe.pk, step['name']], pipe_ignore=True))
runner  = pipeline(pipes).run()
runner.get_result(block=True, timeout=180_000*len(fits_files))
pipes = []
for step in steps[0:1]:
    pipeline_cls = PipelineProcess.get_subclass(step['name'])
    inputs = {f: pipeline_cls.inputs[f]['default'] for f in pipeline_cls.inputs}
    inputs.update(step['inputs'])
    print(f"  Performing pipeline step {step['name']}")
    pipe = pipeline_cls.create_timestamped(inputs)
#                self.stdout.write(f"  PK={pipe.pk} for {step['name']}")
    pipes.append(run_pipeline.message_with_options(args=[pipe.pk, step['name']], pipe_ignore=True))
runner  = pipeline(pipes).run()
pipes = []
for step in steps[0:1]:
    pipeline_cls = PipelineProcess.get_subclass(step['name'])
    inputs = {f: pipeline_cls.inputs[f]['default'] for f in pipeline_cls.inputs}
    inputs.update(step['inputs'])
    print(f"  Performing pipeline step {step['name']}")
    pipe = pipeline_cls.create_timestamped(inputs)
#                self.stdout.write(f"  PK={pipe.pk} for {step['name']}")
    pipes.append(run_pipeline.message_with_options(args=[pipe.pk, step['name']], pipe_ignore=True))
runner  = pipeline(pipes).run()
pipes = []
for step in steps[1:2]:
    pipeline_cls = PipelineProcess.get_subclass(step['name'])
    inputs = {f: pipeline_cls.inputs[f]['default'] for f in pipeline_cls.inputs}
    inputs.update(step['inputs'])
    print(f"  Performing pipeline step {step['name']}")
    pipe = pipeline_cls.create_timestamped(inputs)
#                self.stdout.write(f"  PK={pipe.pk} for {step['name']}")
    pipes.append(run_pipeline.message_with_options(args=[pipe.pk, step['name']], pipe_ignore=True))
runner  = pipeline(pipes).run()
inputs
os.path.exists(inputs['ldac_catalog'])
def file_mapping(origin='LCO'):
    mapping = {'LCO' : { 'proc-astromfit' : ('e91.fits', 'e91_ldac.fits'),
                         'proc-extract' : ('e91.fits', 'e92.fits'),
                         'proc-zeropoint' : ('e91.fits', 'e92_ldac.fits'),
                         'final_catalog_type' : 'BANZAI_LDAC'
                       },
               'SWOPE' : { 'proc-astromfit' : ('.fits', '_ldac.fits'),
                           'proc-extract' : ('.fits', '-e72.fits'),
                           'proc-zeropoint' : ('.fits', '-e72_ldac.fits'),
                           'final_catalog_type' : 'SWOPE_LDAC'
                       },
               'MRO'  : { 'proc-astromfit' : ('e61.fits', 'e61_ldac.fits'),
                          'proc-extract' : ('e61.fits', 'e62.fits'),
                          'proc-zeropoint' : ('e91.fits', 'e62_ldac.fits'),
                          'final_catalog_type' : 'MRO_LDAC'
                       },
              }
    return mapping[origin]
fits_file
mapping['proc-astromfit'][0], mapping['proc-astromfit'][1]
origin
fits_files[0]
fits_files
fits_files, fits_catalogs = determine_images_and_catalogs(self, dataroot, red_level='e61') # red_level must be null to pickup Swope/MRO data
options = {'tempdir' : 'Temp_cvc_multiap', 'refcat' : 'GAIA-DR2', 'zp_tolerance' : 0.1, 'overwrite' : False, 'color_const' : True, 'solar' : False}
catalog_type = 'FITS_LDAC_MULTIAPER'
file_index = fits_files.index(os.path.join(dataroot, 'fm230225.0040-e61.fits'))
fits_filepath = fits_files[file_index]
fits_file = os.path.basename(fits_filepath)
origin = 'LCO'
if 'rccd' in fits_file:
    origin = 'SWOPE'
elif 'fm2' in fits_files[0]:
    origin = 'MRO'
mapping = file_mapping(origin)
steps = [{
            'name'   : 'proc-extract',
            'inputs' : {'fits_file':fits_filepath,
                       'datadir': os.path.join(dataroot, options['tempdir']),
                       'overwrite' : options['overwrite'],
                       'catalog_type' : catalog_type}
        },
        {
            'name'   : 'proc-astromfit',
            'inputs' : {'fits_file' : fits_filepath,
                        'ldac_catalog' : os.path.join(dataroot, options['tempdir'], fits_file.replace(mapping['proc-astromfit'][0], mapping['proc-astromfit'][1])),
                        'datadir' : os.path.join(dataroot, options['tempdir'])
                        }
        },
        {
            'name'   : 'proc-extract',
            'inputs' : {'fits_file': os.path.join(dataroot, options['tempdir'], fits_file.replace(mapping['proc-extract'][0], mapping['proc-extract'][1])),
                       'datadir': os.path.join(dataroot, options['tempdir']),
                       'overwrite' : options['overwrite'],
                       'catalog_type' : catalog_type}
        },
        {
            'name'   : 'proc-zeropoint',
            'inputs' : {'ldac_catalog' : os.path.join(dataroot, options['tempdir'], fits_file.replace(mapping['proc-zeropoint'][0], mapping['proc-zeropoint'][1])),
                        'datadir' : os.path.join(dataroot, options['tempdir']),
                        'zeropoint_tolerance' : options['zp_tolerance'],
                        'catalog_type' :  mapping['final_catalog_type'],
                        'desired_catalog' : options['refcat'],
                        'color_const' : options['color_const'],
                        'solar' : options['solar']
                        }
        }]
print(f"Running pipeline on {fits_file}, producing {catalog_type} catalogs :")
print (origin)
pipes = []
for step in steps[1:2]:
    pipeline_cls = PipelineProcess.get_subclass(step['name'])
    inputs = {f: pipeline_cls.inputs[f]['default'] for f in pipeline_cls.inputs}
    inputs.update(step['inputs'])
    print(f"  Performing pipeline step {step['name']}")
    pipe = pipeline_cls.create_timestamped(inputs)
#                self.stdout.write(f"  PK={pipe.pk} for {step['name']}")
    pipes.append(run_pipeline.message_with_options(args=[pipe.pk, step['name']], pipe_ignore=True))
runner  = pipeline(pipes).run()
options = determine_scamp_options(fits_catalog_path, external_cat_name=refcatalog, distort_degrees=distort_degrees)
inputs
fits_catalog_path = inputs['ldac_catalog']
dest_dir
out_path
out_path = inputs.get('datadir')
out_path
dest_dir = out_path
refcatalog = '/apophis/eng/rocks/MRO/data_mrocal/mro_230225/Temp_cvc_multiap/GAIA-DR2_110.13+28.96_6.7771mx6.7771m.cat'
scamp_config_file = default_scamp_config_files()[0]
scamp_config_file
options = determine_scamp_options(fits_catalog_path, external_cat_name=refcatalog, distort_degrees=distort_degrees)
options = determine_scamp_options(fits_catalog_path, external_cat_name=refcatalog, distort_degrees=None)
options
fits_catalog = os.path.basename(fits_catalog_path)
if fits_catalog != fits_catalog_path:
    fits_catalog = os.path.join(dest_dir, fits_catalog)
    # If the file exists and is a link (or a broken link), then remove it
    if os.path.lexists(fits_catalog):
        if os.path.islink(fits_catalog):
            os.unlink(fits_catalog)
            os.symlink(fits_catalog_path, fits_catalog)
cmdline = "%s %s -c %s %s" % ( binary, fits_catalog, scamp_config_file, options )
cmdline = cmdline.rstrip()
binary = find_binary("scamp")
fits_catalog = os.path.basename(fits_catalog_path)
if fits_catalog != fits_catalog_path:
    fits_catalog = os.path.join(dest_dir, fits_catalog)
    # If the file exists and is a link (or a broken link), then remove it
    if os.path.lexists(fits_catalog):
        if os.path.islink(fits_catalog):
            os.unlink(fits_catalog)
            os.symlink(fits_catalog_path, fits_catalog)
cmdline = "%s %s -c %s %s" % ( binary, fits_catalog, scamp_config_file, options )
cmdline = cmdline.rstrip()
print(cmdline)
inputs
inputs['fits_file']
hdulist = fits.open(inputs['fits_file'], mode='update')
prihdr = hdulist[0].header
filter_val = prihdr.get('FILTER', None)
filter_val
get_ipython().run_line_magic('pinfo', 'convert_value')
convert_value('filter', filter_val)
convert_value('filter', 'R')
hdulist.close()
add_l1filter(inputs['fits_file'])
pipes = []
for step in steps[0:1]:
    pipeline_cls = PipelineProcess.get_subclass(step['name'])
    inputs = {f: pipeline_cls.inputs[f]['default'] for f in pipeline_cls.inputs}
    inputs.update(step['inputs'])
    print(f"  Performing pipeline step {step['name']}")
    pipe = pipeline_cls.create_timestamped(inputs)
#                self.stdout.write(f"  PK={pipe.pk} for {step['name']}")
    pipes.append(run_pipeline.message_with_options(args=[pipe.pk, step['name']], pipe_ignore=True))
runner  = pipeline(pipes).run()
WCS
w = WCS(naxis=2)
fits_file
fits_filepath
fits_header, junk_table, cattype = open_fits_catalog(fits_filepath, header_only=True)
fits_header
WCS(fits_header)
fits_filepath
fits_filepath.replace('0040','0042')
fits_filepath_wcs = fits_filepath.replace('0040','0042')
fits_header_wcs, junk_table, cattype = open_fits_catalog(fits_filepath_wcs, header_only=True)
WCS(fits_header_wcs)
fits_header_wcs
fits_filepath_wcs 
fits_filepath_wcs = fits_filepath.replace('0040','0042').replace('e61', 'e61_wcs')
fits_header_wcs, junk_table, cattype = open_fits_catalog(fits_filepath_wcs, header_only=True)
WCS(fits_header_wcs)
w_fit = WCS(fits_header_wcs)
w_fit.wcs.cdelt
w_fit.wcs.cdelt*3600
pixscale
pixscale = 0.13045502719133564 * fits_header_wcs.get('XBINNING', 1)
pixscale
w
fits_header['CRVAL1']
fits_header['RA']
fits_header_wcs['CRVAL1']
fits_header_wcs['CRVAL1'], fits_header_wcs
fits_header_wcs['CRVAL1'], fits_header_wcs['RA']
Angle
Angle(fits_header_wcs['RA'])
Angle(fits_header_wcs['RA'], unit='hms')
Angle(fits_header_wcs['RA'], unit=u.hourangle)
ra = Angle(fits_header_wcs['RA'], unit=u.hourangle)
ra.to(u.deg)
fits_header_wcs['CRVAL1'], ra.to(u.deg)
fits_files, fits_catalogs = determine_images_and_catalogs(self, dataroot, red_level='e61_wcs') # red_level must be null to pickup Swope/MRO data
fits_files
options = {'tempdir' : 'Temp_cvc_multiap', 'refcat' : 'GAIA-DR2', 'zp_tolerance' : 0.1, 'overwrite' : False, 'color_const' : True, 'solar' : False}
catalog_type = 'FITS_LDAC_MULTIAPER'
file_index = fits_files.index(os.path.join(dataroot, 'fm230225.0042-e61_wcs.fits'))
fits_filepath = fits_files[file_index]
fits_file = os.path.basename(fits_filepath)
origin = 'LCO'
if 'rccd' in fits_file:
    origin = 'SWOPE'
elif 'fm2' in fits_files[0]:
    origin = 'MRO'
mapping = file_mapping(origin)
steps = [{
            'name'   : 'proc-extract',
            'inputs' : {'fits_file':fits_filepath,
                       'datadir': os.path.join(dataroot, options['tempdir']),
                       'overwrite' : options['overwrite'],
                       'catalog_type' : catalog_type}
        },
        {
            'name'   : 'proc-astromfit',
            'inputs' : {'fits_file' : fits_filepath,
                        'ldac_catalog' : os.path.join(dataroot, options['tempdir'], fits_file.replace(mapping['proc-astromfit'][0], mapping['proc-astromfit'][1])),
                        'datadir' : os.path.join(dataroot, options['tempdir'])
                        }
        },
        {
            'name'   : 'proc-extract',
            'inputs' : {'fits_file': os.path.join(dataroot, options['tempdir'], fits_file.replace(mapping['proc-extract'][0], mapping['proc-extract'][1])),
                       'datadir': os.path.join(dataroot, options['tempdir']),
                       'overwrite' : options['overwrite'],
                       'catalog_type' : catalog_type}
        },
        {
            'name'   : 'proc-zeropoint',
            'inputs' : {'ldac_catalog' : os.path.join(dataroot, options['tempdir'], fits_file.replace(mapping['proc-zeropoint'][0], mapping['proc-zeropoint'][1])),
                        'datadir' : os.path.join(dataroot, options['tempdir']),
                        'zeropoint_tolerance' : options['zp_tolerance'],
                        'catalog_type' :  mapping['final_catalog_type'],
                        'desired_catalog' : options['refcat'],
                        'color_const' : options['color_const'],
                        'solar' : options['solar']
                        }
        }]
print(f"Running pipeline on {fits_file}, producing {catalog_type} catalogs :")
pipes = []
for step in steps[0:1]:
    pipeline_cls = PipelineProcess.get_subclass(step['name'])
    inputs = {f: pipeline_cls.inputs[f]['default'] for f in pipeline_cls.inputs}
    inputs.update(step['inputs'])
    print(f"  Performing pipeline step {step['name']}")
    pipe = pipeline_cls.create_timestamped(inputs)
#                self.stdout.write(f"  PK={pipe.pk} for {step['name']}")
    pipes.append(run_pipeline.message_with_options(args=[pipe.pk, step['name']], pipe_ignore=True))
runner  = pipeline(pipes).run()
header
from astropy.coordinates import SkyCoord
w = WCS(naxis=2)
w.wcs.crpix = [fits_header['NAXIS1']/2.0, fits_header['NAXIS2']/2.0]
w
w.wcs.cdelt = np.array([-pixscale/3600.0, pixscale/3600.0])
w
pixscale
tel_pos = SkyCoord(fits_header['RA'], fits_header['DEC'], unit=(u.hourangle, u.deg))
tel_pos
w.wcs.crval = [tel_pos.ra.deg, tel_pos.dec.deg]
w
w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
w
w.naxis
w.wcs.naxis
w.wcs.naxis
w.wcs.naxis = (512,512)
w.to_header()
wcs_header = w.to_header()
get_ipython().run_line_magic('pinfo', 'wcs_header.totextfile')
get_ipython().run_line_magic('pinfo', 'wcs_header.tofile')
inputs
wcs_header.tofile('/apophis/eng/rocks/MRO/data_mrocal/mro_230225/Temp_cvc_multiap/fm230225.0040-e61_ldac.ahead')
get_ipython().run_line_magic('pinfo', 'wcs_header.tofile')
wcs_header.tofile('/apophis/eng/rocks/MRO/data_mrocal/mro_230225/Temp_cvc_multiap/fm230225.0040-e61_ldac.ahead', sep='\\n')
wcs_header.tofile('/apophis/eng/rocks/MRO/data_mrocal/mro_230225/Temp_cvc_multiap/fm230225.0040-e61_ldac.ahead', sep='\\n', clobber=True)
get_ipython().run_line_magic('pinfo', 'wcs_header.tofile')
wcs_header.tofile('/apophis/eng/rocks/MRO/data_mrocal/mro_230225/Temp_cvc_multiap/fm230225.0040-e61_ldac.ahead', sep='\\n', overwrite=True)
wcs_header.totextfile('/apophis/eng/rocks/MRO/data_mrocal/mro_230225/Temp_cvc_multiap/fm230225.0040-e61_ldac.ahead', sep='\\n', overwrite=True)
wcs_header.totextfile('/apophis/eng/rocks/MRO/data_mrocal/mro_230225/Temp_cvc_multiap/fm230225.0040-e61_ldac.ahead', overwrite=True)
status, fits_file_output = self.update_wcs(fits_file, ldac_catalog, out_path)
new_ldac_catalog = '/apophis/eng/rocks/MRO/data_mrocal/mro_230225/Temp_cvc_multiap/fm230225.0040-e61_ldac.fits'
scamp_file = os.path.basename(new_ldac_catalog).replace('.fits', '.head' )
scamp_file = os.path.join(dest_dir, scamp_file)
scamp_xml_file = os.path.basename(new_ldac_catalog).replace('.fits', '.xml' )
scamp_xml_file = os.path.join(dest_dir, scamp_xml_file)
fits_file = fits_file.replace('[SCI]', '')
fits_file_output = increment_red_level(fits_file)
fits_file_output
fits_file
fits_file = 'fm230225.0042-e61.fits'
fits_file_output = increment_red_level(fits_file)
fits_file_output
fits_file_output = 'fm230225.0042-e62.fits'
fits_file_output = os.path.join(dest_dir, fits_file_output.replace('[SCI]', ''))
fits_file_output
status, new_header = updateFITSWCS(fits_file, scamp_file, scamp_xml_file, fits_file_output)
fits_file
fits_filepath
fits_filepath.replace('_wcs','')
fits_file = fits_filepath.replace('_wcs','')
status, new_header = updateFITSWCS(fits_file, scamp_file, scamp_xml_file, fits_file_output)
scamp_info = get_scamp_xml_info(scamp_xml_file)
scamp_info
scamp_info['xy_contrast'] < 1.4 or scamp_info['num_match'] < 4
scamp_head_fh = open(scamp_file, 'r')
lines = scamp_head_fh.readlines()
lines
for line in lines:
    if 'HISTORY' in line:
        # XXX This should really be a regexp...
        wcssolvr = str(line[34:39]+'-'+line[48:54])
        wcssolvr = wcssolvr.rstrip()
    if 'CTYPE1' in line:
        ctype1 = line[9:31].strip().replace("'", "")
    if 'CTYPE2' in line:
        ctype2 = line[9:31].strip().replace("'", "")
    if 'CUNIT1' in line:
        # Trim spaces, remove single quotes
        cunit1 = line[9:31].strip().replace("'", "")
    if 'CUNIT2' in line:
        cunit2 = line[9:31].strip().replace("'", "")
    if 'CRVAL1' in line:
        crval1 = float(line[9:31])
    if 'CRVAL2' in line:
        crval2 = float(line[9:31])
    if 'CRPIX1' in line:
        crpix1 = float(line[9:31])
    if 'CRPIX2' in line:
        crpix2 = float(line[9:31])
    if 'CD1_1' in line:
        cd1_1 = float(line[9:31])
    if 'CD1_2' in line:
        cd1_2 = float(line[9:31])
    if 'CD2_1' in line:
        cd2_1 = float(line[9:31])
    if 'CD2_2' in line:
        cd2_2 = float(line[9:31])
    if 'ASTIRMS1' in line:
        astirms1 = round(float(line[9:31]), 7)
    if 'ASTIRMS2' in line:
        astirms2 = round(float(line[9:31]), 7)
    if 'ASTRRMS1' in line:
        astrrms1 = round(float(line[9:31])*3600.0, 5)
    if 'ASTRRMS2' in line:
        astrrms2 = round(float(line[9:31])*3600.0, 5)
    if 'PV1_' in line or 'PV2_' in line:
        keyword = <redacted>
        value = float(line[9:31])
        pv_terms.append((keyword, value))
scamp_head_fh.close()
wcsrfcat = scamp_info['wcs_refcat']
wcsimcat = scamp_info['wcs_imagecat']
wcsnref = scamp_info['num_refstars']
wcsmatch = scamp_info['num_match']
wccattyp = scamp_info['wcs_cattype']
secpix = round(scamp_info['pixel_scale'], 6)
file_bits = fits_file_output.split(os.extsep)
file_bits

# Update filenames in DB
mro_blocks = Block.objects.filter(superblock__proposal__code='evr_neo')

for block in mro_blocks:
    print(block)
    frames = Frame.objects.filter(block=block)
    for frame in frames:
        frame.filename = frame.filename.replace('.0', '-0')
        frame.save()
        
fits_files, fits_catalogs = determine_images_and_catalogs(self, dataroot, red_level='e61') # red_level must be null to pickup Swope/MRO data
fits_files
mapping = file_mapping(origin)

header, cattype = get_header(fits_filepath)
fits_filepath
cattype
header
mro_blocks
mro_block = mro_blocks[-1]
mro_block = mro_blocks[len(mro_blocks)-1]
mro_block
mro_block.get_blockuid
mro_block.get_blockuid
mro_block.get_blockuid
fits_files, fits_catalogs = determine_images_and_catalogs(self, dataroot, red_level='e61') # red_level must be null to pickup Swope/MRO data
fits_files, fits_catalogs = determine_images_and_catalogs(self, dataroot, red_level='e61') # red_level must be null to pickup Swope/MRO data
fits_files, fits_catalogs = determine_images_and_catalogs(self, dataroot, red_level='e61') # red_level must be null to pickup Swope/MRO data


w = WCS(fits_header)
if w.is_celestial is False:
    new_wcs = WCS(naxis=2)
    new_wcs.wcs.crpix = [fits_header['NAXIS1']/2.0, fits_header['NAXIS2']/2.0]
    pixscale = 0.1323658386327315
    x_pixscale = pixscale * fits_header['XBINNING']
    y_pixscale = pixscale * fits_header['YBINNING']
    # Assume North up East left
    new_wcs.wcs.cdelt = np.array([-x_pixscale/3600.0, y_pixscale/3600.0])
    tel_pos = coord.SkyCoord(fits_header['RA'], fits_header['DEC'], unit=(u.hourangle, u.deg))
    new_wcs.wcs.crval = [tel_pos.ra.deg, tel_pos.dec.deg]
    new_wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
new_wcs
new_wcs._naxis = (fits_header['NAXIS1'], fits_header['NAXIS2'])
new_wcs
fits_header
fits_header.update(new_wcs)
fits_header.update(new_wcs.to_header())
fits_header
fits_header, junk_table, cattype = open_fits_catalog(fits_filepath, header_only=True)
fits_header
from photometrics.catalog_subs import create_initial_MRO_wcs
fits_filepath
fits_filepath = '/apophis/eng/rocks/MRO/data_mrocal/mro_230225/fm230225-0002-e61.fits'
create_initial_MRO_wcs(fits_filepath)
create_initial_MRO_wcs(fits_filepath)
fits_files, fits_catalogs = determine_images_and_catalogs(self, dataroot, red_level='-e61') # red_level must be null to pickup Swope/MRO data
fits_files
def file_mapping(origin='LCO'):
    mapping = {'LCO' : { 'proc-astromfit' : ('e91.fits', 'e91_ldac.fits'),
                         'proc-extract' : ('e91.fits', 'e92.fits'),
                         'proc-zeropoint' : ('e91.fits', 'e92_ldac.fits'),
                         'final_catalog_type' : 'BANZAI_LDAC'
                       },
               'SWOPE' : { 'proc-astromfit' : ('.fits', '_ldac.fits'),
                           'proc-extract' : ('.fits', '-e72.fits'),
                           'proc-zeropoint' : ('.fits', '-e72_ldac.fits'),
                           'final_catalog_type' : 'SWOPE_LDAC'
                       },
               'MRO'  : { 'proc-astromfit' : ('e61.fits', 'e61_ldac.fits'),
                          'proc-extract' : ('e61.fits', 'e62.fits'),
                          'proc-zeropoint' : ('e61.fits', 'e62_ldac.fits'),
                          'final_catalog_type' : 'MRO_LDAC'
                       },
              }
    return mapping[origin]
options = {'tempdir' : 'Temp_cvc_multiap', 'refcat' : 'GAIA-DR2', 'zp_tolerance' : 0.1, 'overwrite' : False, 'color_const' : True, 'solar' : False}
catalog_type = 'FITS_LDAC_MULTIAPER'
file_index = fits_files.index(os.path.join(dataroot, 'fm230225-0002-e61.fits'))
fits_filepath = fits_files[file_index]
fits_file = os.path.basename(fits_filepath)
origin = 'LCO'
if 'rccd' in fits_file:
    origin = 'SWOPE'
elif 'fm2' in fits_files[0]:
    origin = 'MRO'
mapping = file_mapping(origin)
steps = [{
            'name'   : 'proc-prepare',
            'inputs' : {'fits_file':fits_filepath,
                        'origin': origin}
         },
         {
            'name'   : 'proc-extract',
            'inputs' : {'fits_file':fits_filepath,
                       'datadir': os.path.join(dataroot, options['tempdir']),
                       'overwrite' : options['overwrite'],
                       'catalog_type' : catalog_type}
        },
        {
            'name'   : 'proc-astromfit',
            'inputs' : {'fits_file' : fits_filepath,
                        'ldac_catalog' : os.path.join(dataroot, options['tempdir'], fits_file.replace(mapping['proc-astromfit'][0], mapping['proc-astromfit'][1])),
                        'datadir' : os.path.join(dataroot, options['tempdir'])
                        }
        },
        {
            'name'   : 'proc-extract',
            'inputs' : {'fits_file': os.path.join(dataroot, options['tempdir'], fits_file.replace(mapping['proc-extract'][0], mapping['proc-extract'][1])),
                       'datadir': os.path.join(dataroot, options['tempdir']),
                       'overwrite' : options['overwrite'],
                       'catalog_type' : catalog_type}
        },
        {
            'name'   : 'proc-zeropoint',
            'inputs' : {'ldac_catalog' : os.path.join(dataroot, options['tempdir'], fits_file.replace(mapping['proc-zeropoint'][0], mapping['proc-zeropoint'][1])),
                        'datadir' : os.path.join(dataroot, options['tempdir']),
                        'zeropoint_tolerance' : options['zp_tolerance'],
                        'catalog_type' :  mapping['final_catalog_type'],
                        'desired_catalog' : options['refcat'],
                        'color_const' : options['color_const'],
                        'solar' : options['solar']
                        }
        }]
print(f"Running pipeline on {fits_file}, producing {catalog_type} catalogs :")


pipes = []
for step in steps[0:2]:
    pipeline_cls = PipelineProcess.get_subclass(step['name'])
    inputs = {f: pipeline_cls.inputs[f]['default'] for f in pipeline_cls.inputs}
    inputs.update(step['inputs'])
    print(f"  Performing pipeline step {step['name']}")
    pipe = pipeline_cls.create_timestamped(inputs)
#                self.stdout.write(f"  PK={pipe.pk} for {step['name']}")
    pipes.append(run_pipeline.message_with_options(args=[pipe.pk, step['name']], pipe_ignore=True))
runner  = pipeline(pipes).run()
