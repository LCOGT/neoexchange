# coding: utf-8
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
from django.db.models import Q
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
swope_header, swope_cattype = get_header('/apophis/eng/rocks/Swope/data_lcoswoperaw/ut220926/ccd1246c4_220926.fits')
swope_cattype
swope_header
obs_night = datetime.strptime(swope_header['groupid'], '%d%b%Y')
obs_night
obs_night.strftime('%d%b%Y')
get_ipython().system('ls ~/git/neoexchange*/neoexchange/photometrics/*swope*\\')
get_ipython().system('ls ~/git/neoexchange*/neoexchange/photometrics/*swope*')
get_ipython().system('ls ~/git/neoexchange*/neoexchange/photometrics/tests/*swope*')
(10*0.435)/60.0
hdulist = fits.open('photometrics/tests/mro_test_frame.fits')
hdulist.info()
hdulist[0].header
mro_wcs = WCS(hdulist[0].header)
mro_wcs
mro_wcs.pc
mro_wcs.wcs.pc
test_ldacfilename = os.path.join('photometrics', 'tests', 'ldac_test_catalog.fits')
hdulist = fits.open(test_ldacfilename)
header_array = hdulist[1].data[0][0]
header = fits_ldac_to_header(header_array)
test_ldactable = hdulist[2].data
test_ldactable.columns
test_ldactable['FLUX_AUTO']
test_ldactable['FLUX_AUTO']?
flux_col= test_ldactable['FLUX_AUTO']
test_ldactable.columns["FLUX_AUTO"]
test_ldactable.columns["FLUX_AUTO"].name
test_ldactable.columns["FLUX_AUTO"].name = 'FLUX_APER'
test_ldactable.columns["FLUXERR_AUTO"].name = 'FLUXERR_APER'
hdulist.writeto(os.path.join('photometrics', 'tests', 'ldac_test_catalog_aper.fits'))
get_ipython().system('topcat photometrics/tests/ldac_test_catalog_aper.fits&')
get_ipython().system('geany >& /dev/null&')


options = { 'fitspattern' : 'fm*.????.fits'}
dataroot = '/apophis/eng/rocks/MRO/data_mrocal'
obs_date = '230225'
object_dirs = [x[0] for x in os.walk(dataroot) if ('Didymos' in x[0] or '65803' in x[0] or obs_date in x[0][-8:]) and 'Temp_cvc' not in x[0]]
object_dirs
rock = object_dirs[0]
datadir = os.path.join(dataroot, rock)
fits_files = get_fits_files(datadir, options['fitspattern'])
fits_files
first_file = fits_files[0]
fits_header, dummy_table, cattype = open_fits_catalog(first_file, header_only=True)
header = get_catalog_header(fits_header, cattype)
header
tracking_num = header.get('tracking_number', None)
tracking_num_nopad = tracking_num.lstrip('0')

sblocks = SuperBlock.objects.filter(Q(tracking_number=tracking_num)|Q(tracking_number=tracking_num_nopad))
sblocks
name = header.get('object_name', None)
name
pos_0096 = np.array([237.26,107.79])
pos_0095 = np.array([156.80,133.23])
pos_0096-pos_0095
header
first_file = fits_files[0]
fits_header, dummy_table, cattype = open_fits_catalog(first_file, header_only=True)
header = get_catalog_header(fits_header, cattype)
heade['site_id']
header['site_id']
name = header.get('object_name', None)
if name:
    # Take out any parentheses e.g. (28484)
    name = name.rstrip().replace('(', '').replace(')', '').replace('Didymos', '65803')
    # MRO-specific oddities
    if header.get('site_id', '') == 'MRO':
        name = name.replace('R', '').replace('V', '').replace('didcomps', 'didymos').replace('comps', 'mos').replace('comp', 'mos').replace('compc', 'mos')
        name = name.replace('didymos', '65803')
bodies = Body.objects.filter(Q(provisional_name__exact = name )|Q(provisional_packed__exact = name)|Q(name__exact = name))
bodies
name

                        
for name in ['didcompsR', 'didycompcV', 'didycompR', 'didycompsR', 'didycompsV', 'didymosR', 'didymosV', 'didymosVR']:
                        name = name.rstrip().replace('(', '').replace(')', '').replace('Didymos', '65803')
                        # MRO-specific oddities
                        if header.get('site_id', '') == 'MRO':
                            name = name.replace('R', '').replace('V', '').replace('didcomps', 'didymos').replace('comps', 'mos').replace('compc', 'mos').replace('comp', 'mos')
                            name = name.replace('didymos', '65803')
            
                        print(name)
                        

body = bodies[0]
sblock_params = { 'active': True,
                  'block_start': header.get('block_start'),
                  'block_end'  : header.get('block_end'),
                  'body': body,
                  'groupid'   : header.get('groupid', ''),
                  'proposal' : Proposal.objects.get(code=header.get('proposal', '')),
                  'tracking_number': tracking_num,
                }
new_sblock, created = SuperBlock.objects.get_or_create(**sblock_params)
get_ipython().run_line_magic('history', '')
