# coding: utf-8
fits_files = get_fits_files(datadir)
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
origin = 'LCO'
if 'rccd' in fits_files[0]:
    origin = 'SWOPE'
elif 'fm2' in fits_files[0]:
    origin = 'MRO'
mapping = self.file_mapping(origin)
datadir
dataroot = '/apophis/eng/rocks/MRO/data_mrocal/mro_230225/'
fits_files, fits_catalogs = determine_images_and_catalogs(None, dataroot) #, red_level='') # red_level must be null to pickup Swope data
fits_files, fits_catalogs = determine_images_and_catalogs(None, dataroot, red_level='') # red_level must be null to pickup Swope/MRO data
origin = 'LCO'
if 'rccd' in fits_files[0]:
    origin = 'SWOPE'
elif 'fm2' in fits_files[0]:
    origin = 'MRO'
mapping = self.file_mapping(origin)
origin = 'LCO'
if 'rccd' in fits_files[0]:
    origin = 'SWOPE'
elif 'fm2' in fits_files[0]:
    origin = 'MRO'
mapping = file_mapping(origin)
get_ipython().run_line_magic('cpaste', '')
origin = 'LCO'
if 'rccd' in fits_files[0]:
    origin = 'SWOPE'
elif 'fm2' in fits_files[0]:
    origin = 'MRO'
mapping = file_mapping(origin)
mapping
origin = 'LCO'
if 'rccd' in fits_files[0]:
    origin = 'SWOPE'
elif 'fm2' in fits_files[0]:
    origin = 'MRO'
mapping = file_mapping(origin)
mapping
fits_files[0]
origin
def file_mapping(origin='LCO'):
    mapping = {'LCO' : { 'proc-astromfit' : ('e91.fits', 'e91_ldac.fits'),
                         'proc-extract' : ('e91.fits', 'e92.fits'),
                         'proc-zeropoint' : ('e91.fits', 'e92_ldac.fits')
                       },
               'SWOPE' : { 'proc-astromfit' : ('.fits', '_ldac.fits'),
                           'proc-extract' : ('.fits', '-e72.fits'),
                           'proc-zeropoint' : ('.fits', '-e72_ldac.fits')
                       },
               'MRO'  : { 'proc-astromfit' : ('.fits', '_ldac.fits'),
                          'proc-extract' : ('.fits', '-e62.fits'),
                          'proc-zeropoint' : ('.fits', '-e62_ldac.fits')
                       },
              }
    return mapping[origin]
origin = 'LCO'
if 'rccd' in fits_files[0]:
    origin = 'SWOPE'
elif 'fm2' in fits_files[0]:
    origin = 'MRO'
mapping = file_mapping(origin)
mapping
options = {'tempdir' : 'Temp_cvc_multiap', 'refcat' : 'GAIA-DR2', 'zp_tolerance' : 0.1, 'overwrite' : False, 'color_const' : True, 'solar' : False}
catalog_type = 'FITS_LDAC_MULTIAPER'
file_index = fits_files.index(os.path.join(dataroot, 'lsc1m004-fa03-20220930-0468-e91.fits'))
fits_filepath = fits_files[file_index]
fits_file = os.path.basename(fits_filepath)
origin = 'LCO'
if 'rccd' in fits_file:
    origin = 'SWOPE'
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
                        'catalog_type' : 'BANZAI_LDAC' if origin == 'LCO' else 'MRO_LDAC',
                        'desired_catalog' : options['refcat'],
                        'color_const' : options['color_const'],
                        'solar' : options['solar']
                        }
        }]
print(f"Running pipeline on {fits_file}, producing {catalog_type} catalogs :")
