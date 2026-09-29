# coding: utf-8
from core.models import Body, SuperBlock, Block, Frame, CatalogSources, SourceMeasurement, Proposal
from core.views import determine_images_and_catalogs, compare_NEOx_horizons_ephems

from astrometrics.ephem_subs import horizons_ephem, compute_ephem
from photometrics.catalog_subs import *
from photometrics.pds_subs import *

from matplotlib.dates import HourLocator, DateFormatter
import astropy.units as u
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from django.conf import settings

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
    
obstype ='EXPOSE'
proposal = 'LCO2022B-006'
start_date = datetime(2022,9,26,18)
end_date = datetime(2022,9,27,10)
settings
limit = 1000
base_url = settings.ARCHIVE_FRAMES_URL
archive_url = '%s?limit=%d&start=%s&end=%s&OBSTYPE=%s&PROPID=%s&format=json' % (base_url, limit, start_date, end_date, obstype, proposal)
archive_url
reduction_lvl = '91'
search_url = archive_url + '&RLEVEL=' + reduction_lvl
print("search_url=%s" % search_url)
collection = []
fetch_frames(search_url, collection, auth_headers)
from core.archive_subs import fetch_frames
collection = []
fetch_frames(search_url, collection, auth_headers)
auth_headers = archive_login()
from core.archive_subs import archive_login
auth_headers = archive_login()
collection = []
fetch_frames(search_url, collection, auth_headers)
collection
get_ipython().run_line_magic('pinfo', 'collection')
collection[0]
collection[0]['version_set']
frames['91'] = collection[0]
frames = {}
frames['91'] = [collection[0],]
frames
from core.archive_subs import download_files
download_files(frames, '/apophis/eng/rocks/20220926/New_processing/', True)
frames = {}
frames['91'] = [collection[1:10],]
frames
download_files(frames, '/apophis/eng/rocks/20220926/New_processing/', True)
frames = {}
frames['91'] = collection[1:10]
download_files(frames, '/apophis/eng/rocks/20220926/New_processing/', True)
search_url
collection = []
fetch_frames(search_url, collection, auth_headers)
get_ipython().run_line_magic('pinfo', 'collection')
frames = {}
frames['91'] = collection
download_files(frames, '/apophis/eng/rocks/20220926/New_processing/', True)
download_files(frames, '/apophis/eng/rocks/20220926/New_processing/', True)
from photometrics.catalog_subs import get_fits_files, sort_rocks, find_first_last_frames
out_path = '/apophis/eng/rocks/20220926/New_processing/'
fits_files = get_fits_files(out_path)
fits_files
out_path = '/apophis/eng/rocks/20220926/New_processing/20220926'
fits_files
fits_files = get_fits_files(out_path)
print(len(fits_files))
objects = sort_rocks(fits_files)
objects
ap
apers = np.linspace(1,21,20)
apers
apers = np.linspace(1,20,20)
apers
apers*u.pixel
apers*u.arcsec*pixel_scale
pixel_scale = 0.682*(u.arcsec/u.pixel)
apers*u.arcsec*pixel_scale
(apers*u.arcsec)*pixel_scale
(apers*u.arcsec)/pixel_scale
(2*apers*u.arcsec)/pixel_scale
pixel_scale = 0.68127658*(u.arcsec/u.pixel)
(2*apers*u.arcsec)/pixel_scale
for index, aper in enumerate(apers):
    print(f"{index:>2d}: {(2*aper*u.arcsec)/pixel_scale:.2f}")
    
  
get_ipython().run_line_magic('history', '')
body
body = Body.objects.get(name='65803')
Frame.objects.filter(block__body=body, instrument='ef02').count()
Frame.objects.filter(block__body=body, instrument='ef02', frametype=Frame.BANZAI_RED_FRAMETYPE).count()
Frame.objects.filter(block__body=body, instrument='ef02', frametype=Frame.BANZAI_RED_FRAMETYPE).distinct('filter')
import warnings
warnings.simplefilter('ignore', FITSFixedWarning)
Frame.objects.filter(block__body=body, instrument='ef02', frametype=Frame.BANZAI_RED_FRAMETYPE).distinct('filter')
Frame.objects.filter(block__body=body, instrument='ef02', frametype=Frame.BANZAI_RED_FRAMETYPE).distinct('filter').values_list('filter')
for obs_filter in Frame.objects.filter(block__body=body, instrument='ef02', frametype=Frame.BANZAI_RED_FRAMETYPE).distinct('filter').values_list('filter'):
    print(obs_filter, Frame.objects.filter(block__body=body, instrument='ef02', frametype=Frame.BANZAI_RED_FRAMETYPE, filter=obs_filter).count())
    
for obs_filter in Frame.objects.filter(block__body=body, instrument='ef02', frametype=Frame.BANZAI_RED_FRAMETYPE).distinct('filter').values_list('filter'):
    print(obs_filter, Frame.objects.filter(block__body=body, instrument='ef02', frametype=Frame.BANZAI_RED_FRAMETYPE, filter=obs_filter[0]).count())
    
    

    
for camera in ['ef02', 'ef03', 'ef04']:
    print(camera,':')
    for obs_filter in Frame.objects.filter(block__body=body, instrument=camera, frametype=Frame.BANZAI_RED_FRAMETYPE).distinct('filter').values_list('filter', flat=True):
        print(obs_filter, Frame.objects.filter(block__body=body, instrument=camera, frametype=Frame.BANZAI_RED_FRAMETYPE, filter=obs_filter).count(), ', ', end='')
    print()
    
body
Frame.objects.filter(block__body=body, instrument=camera, frametype=Frame.BANZAI_RED_FRAMETYPE, filter='clear').count()
Frame.objects.filter(block__body=body, instrument='ef03', frametype=Frame.BANZAI_RED_FRAMETYPE, filter='clear').count()
for frame in Frame.objects.filter(block__body=body, instrument='ef03', frametype=Frame.BANZAI_RED_FRAMETYPE, filter='clear').order_by('midpoint'):
    print(frame.filename)
    

for camera in ['ef02', 'ef03', 'ef04']:
    print(camera,':')
    for obs_filter in Frame.objects.filter(block__body=body, block__block_start__gte=start, block__block_end__lt=end, instrument=camera, frametype=Frame.BANZAI_RED_FRAMETYPE).distinct('filter').values_list('filter', flat=True):
        print(obs_filter, Frame.objects.filter(block__body=body, block__block_start__gte=start, block__block_end__lt=end, instrument=camera, frametype=Frame.BANZAI_RED_FRAMETYPE, filter=obs_filter).count(), ', ', end='')
    print()
    
camera='ef04'
Frame.objects.filter(block__body=body, block__block_start__gte=start, block__block_end__lt=end, instrument=camera, frametype=Frame.BANZAI_RED_FRAMETYPE, filter='clear').count()
Frame.objects.filter(block__body=body, block__block_start__gte=start, block__block_end__lt=end, instrument=camera, frametype=Frame.BANZAI_RED_FRAMETYPE, filter='clear', exptime__lt=1).count()
Frame.objects.filter(block__body=body, block__block_start__gte=start, block__block_end__lt=end, instrument=camera, frametype=Frame.BANZAI_RED_FRAMETYPE, filter='clear', exptime__gte=2).count()
