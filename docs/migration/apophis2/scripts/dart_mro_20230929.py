# coding: utf-8
get_ipython().system('geany dart_mro_20230921.py&')
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
    
self=None
dataroot = '/apophis/eng/rocks/MRO/data_mrocal'
dataroot = os.path.join(dataroot, 'mro_230225')
fits_files, fits_catalogs = determine_images_and_catalogs(self, dataroot, red_level='-e61') # red_level must be null to pickup Swope/MRO data
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
fits_files[0]
origin
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
Frame.objects.get(filename='fm230225-0002-e61.fits')
Frame.objects.get(filename='fm230225%0002-e61.fits')
Frame.objects.get(filename__startswith='fm230225')
Frame.objects.filter(filename__startswith='fm230225').values_list(filename)
Frame.objects.filter(filename__startswith='fm230225').values_list('filename')
mro_blocks = Block.objects.filter(superblock__proposal__code='evr_neo')
mro_blocks
Frame.objects.filter(filename__startswith='fm230225').first().block
for block in mro_blocks:
    print(block)
    frames = Frame.objects.filter(block=block)
    for frame in frames:
        frame.filename = frame.filename.replace('.0', '-0')
        frame.save()
        
Frame.objects.get(filename='fm230225%0002-e61.fits')
Frame.objects.get(filename='fm230225-0002-e61.fits')
pipes = []
for step in steps[0:3]:
    pipeline_cls = PipelineProcess.get_subclass(step['name'])
    inputs = {f: pipeline_cls.inputs[f]['default'] for f in pipeline_cls.inputs}
    inputs.update(step['inputs'])
    print(f"  Performing pipeline step {step['name']}")
    pipe = pipeline_cls.create_timestamped(inputs)
#                self.stdout.write(f"  PK={pipe.pk} for {step['name']}")
    pipes.append(run_pipeline.message_with_options(args=[pipe.pk, step['name']], pipe_ignore=True))
runner  = pipeline(pipes).run()
pipes = []
for step in steps:
    pipeline_cls = PipelineProcess.get_subclass(step['name'])
    inputs = {f: pipeline_cls.inputs[f]['default'] for f in pipeline_cls.inputs}
    inputs.update(step['inputs'])
    print(f"  Performing pipeline step {step['name']}")
    pipe = pipeline_cls.create_timestamped(inputs)
#                self.stdout.write(f"  PK={pipe.pk} for {step['name']}")
    pipes.append(run_pipeline.message_with_options(args=[pipe.pk, step['name']], pipe_ignore=True))
runner  = pipeline(pipes).run()
pipes = []
for step in steps:
    pipeline_cls = PipelineProcess.get_subclass(step['name'])
    inputs = {f: pipeline_cls.inputs[f]['default'] for f in pipeline_cls.inputs}
    inputs.update(step['inputs'])
    print(f"  Performing pipeline step {step['name']}")
    pipe = pipeline_cls.create_timestamped(inputs)
#                self.stdout.write(f"  PK={pipe.pk} for {step['name']}")
    pipes.append(run_pipeline.message_with_options(args=[pipe.pk, step['name']], pipe_ignore=True))
runner  = pipeline(pipes).run()
cal_filter = map_filter_to_calfilter(header['filter'])
from photometrics.photometry_subs import map_filter_to_calfilter
header, table, refcat = self.setup(catfile, catalog_type, phot_cat_name, min_matches=min_matches)
step
inputs
inputs = step['inputs']
if not inputs.get('datadir'):
    out_path = tmpdir
else:
    out_path = inputs.get('datadir')
fits_file = inputs.get('fits_file')
ldac_catalog = inputs.get('ldac_catalog')
configs_dir = inputs.get('configs_dir')
desired_catalog = inputs.get('desired_catalog')
catfile = inputs.get('ldac_catalog')
catalog_type = inputs.get('catalog_type')
phot_cat_name = inputs.get('desired_catalog')
std_zeropoint_tolerance = inputs.get('zeropoint_tolerance')
color_const = inputs.get('color_const', False)
solar = inputs.get('solar', True)
filename = os.path.basename(catfile)
datadir = os.path.join(os.path.dirname(catfile), '')
header, table = extract_catalog(catfile, catalog_type, flag_filter=7)
header
cal_filter = map_filter_to_calfilter(header['filter'])
cal_filter
cal_filter = map_filter_to_calfilter(header['filter'])
if cal_filter is None:
    print(f"This filter ({header['filter']}) is not calibrateable")
    
cal_filter = map_filter_to_calfilter(header['filter'])
if cal_filter is None:
    print(f"This filter ({header['filter']}) is not calibrateable")
    
steps [-1:]
pipes = []
for step in steps[-1:]:
    pipeline_cls = PipelineProcess.get_subclass(step['name'])
    inputs = {f: pipeline_cls.inputs[f]['default'] for f in pipeline_cls.inputs}
    inputs.update(step['inputs'])
    print(f"  Performing pipeline step {step['name']}")
    pipe = pipeline_cls.create_timestamped(inputs)
#                self.stdout.write(f"  PK={pipe.pk} for {step['name']}")
    pipes.append(run_pipeline.message_with_options(args=[pipe.pk, step['name']], pipe_ignore=True))
runner  = pipeline(pipes).run()
inputs
pipes = []
for step in steps[-1:]:
    pipeline_cls = PipelineProcess.get_subclass(step['name'])
    inputs = {f: pipeline_cls.inputs[f]['default'] for f in pipeline_cls.inputs}
    inputs.update(step['inputs'])
    print(f"  Performing pipeline step {step['name']}")
    pipe = pipeline_cls.create_timestamped(inputs)
#                self.stdout.write(f"  PK={pipe.pk} for {step['name']}")
    pipes.append(run_pipeline.message_with_options(args=[pipe.pk, step['name']], pipe_ignore=True))
runner  = pipeline(pipes).run()
pipes = []
for step in steps[-1:]:
    pipeline_cls = PipelineProcess.get_subclass(step['name'])
    inputs = {f: pipeline_cls.inputs[f]['default'] for f in pipeline_cls.inputs}
    inputs.update(step['inputs'])
    print(f"  Performing pipeline step {step['name']}")
    pipe = pipeline_cls.create_timestamped(inputs)
#                self.stdout.write(f"  PK={pipe.pk} for {step['name']}")
    pipes.append(run_pipeline.message_with_options(args=[pipe.pk, step['name']], pipe_ignore=True))
runner  = pipeline(pipes).run()
pipes = []
for step in steps[-1:]:
    pipeline_cls = PipelineProcess.get_subclass(step['name'])
    inputs = {f: pipeline_cls.inputs[f]['default'] for f in pipeline_cls.inputs}
    inputs.update(step['inputs'])
    print(f"  Performing pipeline step {step['name']}")
    pipe = pipeline_cls.create_timestamped(inputs)
#                self.stdout.write(f"  PK={pipe.pk} for {step['name']}")
    pipes.append(run_pipeline.message_with_options(args=[pipe.pk, step['name']], pipe_ignore=True))
runner  = pipeline(pipes).run()
0.00127107466200016*3600
110.1103280535-110.10504166667
110.10504166667-110.1103280535
1.527796644758E-05*3600
pixscale
pixscale = 0.5213090181350708
pixscale_sinistro = .389
for aper_radius in np.range(1,10,1):
    print(aper_radius)
    
for aper_radius in n.arange(1,10,1):
    print(aper_radius)
    
for aper_radius in np.arange(1,10,1):
    print(aper_radius)
    
for aper_radius in np.arange(1,10+1,1):
    print(aper_radius)
    
pixscale_sinistro *= (u.arcsec/u.pixel)
for aper_radius in np.arange(1,10+1,1):
    print(aper_radius)
    
for aper_radius in np.arange(1,10+1,1)*u.arcsec:
    print(aper_radius)
    
aper_radius
aper_radius.tostring()
aper_radius.tostring
aper_radius.tostring()
aper_radius.to_string()
aper_radius.to_string(?)
get_ipython().run_line_magic('pinfo', 'aper_radius.to_string')
aper_radius.to_string('console')
aper_radius.to_string('unicode')
for aper_radius in np.arange(1,10+1,1)*u.arcsec:
    print(f"{aper_radius:>3.1f}")
    
    
for aper_radius in np.arange(1,10+1,1)*u.arcsec:
    print(f"{aper_radius.value:>3.1f}",end='')
    
    
    
for aper_radius in np.arange(1,10+1,1)*u.arcsec:
    print(f"{aper_radius.value:>3.1f}  ",end='')
    
    
    
    
for aper_radius in np.arange(1,10+1,1)*u.arcsec:
    print(f'{aper_radius.value:>3.1f}\"  ',end='')
    
    
    
    
    
print('   radius=', end='')
for aper_radius in np.arange(1,10+1,1)*u.arcsec:
    print(f'{aper_radius.value:>3.1f}\"  ',end='')
    diam_pixels = aper_radius / pixelscale_sinistro
    print(f'{diam_pixels.value:>5.2f}  ',end='')
print()
print('   radius=', end='')
for aper_radius in np.arange(1,10+1,1)*u.arcsec:
    print(f'{aper_radius.value:>3.1f}\"  ',end='')
    diam_pixels = aper_radius / pixscale_sinistro
    print(f'{diam_pixels.value:>5.2f}  ',end='')
print()
print('   radius=', end='')
for aper_radius in np.arange(1,10+1,1)*u.arcsec:
    print(f'{aper_radius.value:>3.1f}\"  ',end='')
print('\nDiameter=', end='')
for aper_radius in np.arange(1,10+1,1)*u.arcsec:
    diam_pixels = aper_radius / pixscale_sinistro
    print(f'{diam_pixels.value:>5.2f}  ',end='')
print()
print('  radius=', end='')
for aper_radius in np.arange(1,10+1,1)*u.arcsec:
    print(f'{aper_radius.value:>3.1f}\"  ',end='')
print('\nDiameter=', end='')
for aper_radius in np.arange(1,10+1,1)*u.arcsec:
    diam_pixels = aper_radius / pixscale_sinistro
    print(f'{diam_pixels.value:>5.2f}  ',end='')
print()
print('  radius=', end='')
for aper_radius in np.arange(1,10+1,1)*u.arcsec:
    print(f'{aper_radius.value:>3.1f}\"  ',end='')
print('\nDiameter=', end='')
for aper_radius in np.arange(1,10+1,1)*u.arcsec:
    diam_pixels = 2*aper_radius / pixscale_sinistro
    print(f'{diam_pixels.value:>5.2f}  ',end='')
print()
print('  radius=', end='')
for aper_radius in np.arange(1,10+1,1)*u.arcsec:
    print(f'{aper_radius.value:>3.1f}\"  ',end='')
print('\nDiameter=', end='')
for aper_radius in np.arange(1,10+1,1)*u.arcsec:
    diam_pixels = 2*aper_radius / pixscale_sinistro
    print(f'{diam_pixels.value:>5.2f} ',end='')
print()
pixscale_sinistro = 0.389635* (u.arcsec/u.pixel)
print('  radius=', end='')
for aper_radius in np.arange(1,10+1,1)*u.arcsec:
    print(f'{aper_radius.value:>3.1f}\"  ',end='')
print('\nDiameter=', end='')
for aper_radius in np.arange(1,10+1,1)*u.arcsec:
    diam_pixels = 2*aper_radius / pixscale_sinistro
    print(f'{diam_pixels.value:>5.2f} ',end='')
print()
print('  radius= ', end='')
for aper_radius in np.arange(1,10+1,1)*u.arcsec:
    print(f'{aper_radius.value:>3.1f}\"  ',end='')
print('\nDiameter=', end='')
for aper_radius in np.arange(1,10+1,1)*u.arcsec:
    diam_pixels = 2*aper_radius / pixscale_sinistro
    print(f'{diam_pixels.value:>5.2f} ',end='')
print()
print('  radius= ', end='')
for aper_radius in np.arange(1,10+1,1)*u.arcsec:
    print(f'{aper_radius.value:>3.1f}\"  ',end='')
print('\nDiameter=', end='')
for aper_radius in np.arange(1,10+1,1)*u.arcsec:
    diam_pixels = 2*aper_radius / pixscale
    print(f'{diam_pixels.value:>5.2f} ',end='')
print()
pixscale *= u.arcsec/u.pixel
print('  radius= ', end='')
for aper_radius in np.arange(1,10+1,1)*u.arcsec:
    print(f'{aper_radius.value:>3.1f}\"  ',end='')
print('\nDiameter=', end='')
for aper_radius in np.arange(1,10+1,1)*u.arcsec:
    diam_pixels = 2*aper_radius / pixscale
    print(f'{diam_pixels.value:>5.2f} ',end='')
print()
fits_files, fits_catalogs = determine_images_and_catalogs(self, dataroot, red_level='e61') # red_level must be null to pickup Swope/MRO data
fits_files
"5.13,10.27,15.40,20.53,22,25.67,30.80,35.93,41.06,46.20,51.33".split(",")
aps = "5.13,10.27,15.40,20.53,22,25.67,30.80,35.93,41.06,46.20,51.33".split(",")
len(aps)
aps = "3.84,7.67,11.51,15.35,19.18,23.02,26.86,30.69,34.53,38.36".split(",")
len(aps)
print('  radius= ', end='')
for aper_radius in np.arange(1,10+1,1)*u.arcsec:
    print(f'{aper_radius.value:>3.1f}\"  ',end='')
print('\nDiameter=', end='')
for aper_radius in np.arange(1,10+1,1)*u.arcsec:
    diam_pixels = 2*aper_radius / pixscale
    print(f'{diam_pixels.value:>5.2f} ',end='')
print()
aps = "5.13,10.27,15.40,20.53,22,25.67,30.80,35.93,41.06,46.20,51.33".split(",")
for ap in aps:
    ap = ap*u.pixel
    print(ap/2*pixscale_sinistro)
    
for ap in aps:
    ap = ap*u.pixel
    print((ap/2)*pixscale_sinistro)
    
    
aps
for ap in aps:
    ap = float(ap)*u.pixel
    print((ap/2)*pixscale_sinistro)
    
    
for ap in aps:
    ap = float(ap)*u.pixel
    radius=(ap/2)*pixscale_sinistro
    print(f"{ap:.1f}")
    
    
    
for ap in aps:
    ap = float(ap)*u.pixel
    radius=(ap/2)*pixscale_sinistro
    print(f"{radius:.1f}")
    
for i, ap in enumerate(aps):
    ap = float(ap)*u.pixel
    radius=(ap/2)*pixscale_sinistro
    print(f"{radius:.1f}")
    
for i, ap in enumerate(aps):
    ap = float(ap)*u.pixel
    radius=(ap/2)*pixscale_sinistro
    print(f"{i:2d}: {radius:.1f}")
    
for i, ap in enumerate(aps):
    ap = float(ap)*u.pixel
    radius=(ap/2)*pixscale_sinistro
    print(f"{i+1:2d}: {radius:.1f}")
    
for i in range(1,11,1):
    print(i)
    
for i in range(1,11,1):
    ap_rad = i*u.arcsec
    diam_pix = (2*ap_rad)/pixscale
    print(i, diam_pix)
    
for i in range(1,11,1):
    ap_rad = i*u.arcsec
    diam_pix = (2*ap_rad)/pixscale
    print(f"{i:2d}: {diam_pix:.2f}")
    
    
for i in range(1,11,1):
    ap_rad = i*u.arcsec
    diam_pix = (2*ap_rad)/pixscale_sinistro
    print(f"{i:2d}: {diam_pix:.2f}")
    
    
for i in range(1,12,1):
    ap_rad = i*u.arcsec
    diam_pix = (2*ap_rad)/pixscale
    print(f"{i:2d}: {diam_pix:.2f}")
    
    
fm221011-0380-e62.fits
len('fm221011-0380-e62_ldac.fits')
(site_name, site_long, site_lat, site_hgt) = get_sitepos(sitecode)
from astrometrics.ephem_subs import get_sitepos
sblock = SuperBlock.objects.get(tracking_number='MRO-21102022')
sblock.get_telclass()
block_list = Block.objects.filter(superblock=super_block.id)
super_block = sblock
block_list = Block.objects.filter(superblock=super_block.id)
block_list
block = block_list[0]
frames_red = Frame.objects.filter(block=block.id, frametype__in=[Frame.BANZAI_RED_FRAMETYPE]).order_by('filter', 'midpoint')
frames_neox = Frame.objects.filter(block=block.id, frametype__in=[Frame.NEOX_RED_FRAMETYPE]).order_by('filter', 'midpoint')
if frames_neox.filter(zeropoint__isnull=False).count() >= frames_red.filter(zeropoint__isnull=False).count():
    frames_all_zp = frames_neox
else:
    frames_all_zp = frames_red
frames_all_zp
frames = frames_all_zp.filter(zeropoint__isnull=False, zeropoint__gte=0)
data_path = make_data_dir(out_path, model_to_dict(frames_all_zp[0]))
from core.archive_subs import make_data_dir
data_path = make_data_dir(out_path, model_to_dict(frames_all_zp[0]))
from django.forms import model_to_dict
data_path = make_data_dir(out_path, model_to_dict(frames_all_zp[0]))
get_ipython().run_line_magic('history', '')
7.29*12
t_impact = datetime(2022,9,26, 23,14,24.183)
t_impact = datetime(2022,9,26, 23,14,24, int(1e6*0.183))
t_impact
get_ipython().run_line_magic('pinfo', 'timedelta')
t_impact-timedelta(hours=1,minutes=16,seconds=31)
catfile = '/apophis/eng/rocks/MRO/data_mrocal/mro_221122/Temp_cvc_multiap/fm221122-0195-e61_ldac.fits' 
 
cattype = 'MRO_LDAC'
fits_header, junk_table, cattype = open_fits_catalog(catfile, header_only=True)
cattype
header = get_catalog_header(fits_header, cattype)
header
'2m4' in header['tel_id']
fits_files, fits_catalogs = determine_images_and_catalogs(self, dataroot, red_level='-e61') # red_level must be null to pickup Swope/MRO data
dataroot
dataroot = '/apophis/eng/rocks/MRO/data_mrocal'
dataroot = os.path.join(dataroot, 'mro_221122')
fits_files, fits_catalogs = determine_images_and_catalogs(self, dataroot, red_level='-e61') # red_level must be null to pickup Swope/MRO data
options = {'tempdir' : 'Temp_cvc_multiap', 'refcat' : 'GAIA-DR2', 'zp_tolerance' : 0.1, 'overwrite' : False, 'color_const' : True, 'solar' : False}
catalog_type = 'FITS_LDAC_MULTIAPER'
file_index = fits_files.index(os.path.join(dataroot, 'fm221122-0192-e61.fits'))
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
for step in steps:
    pipeline_cls = PipelineProcess.get_subclass(step['name'])
    inputs = {f: pipeline_cls.inputs[f]['default'] for f in pipeline_cls.inputs}
    inputs.update(step['inputs'])
    print(f"  Performing pipeline step {step['name']}")
    pipe = pipeline_cls.create_timestamped(inputs)
#                self.stdout.write(f"  PK={pipe.pk} for {step['name']}")
    pipes.append(run_pipeline.message_with_options(args=[pipe.pk, step['name']], pipe_ignore=True))
runner  = pipeline(pipes).run()
options = {'tempdir' : 'Temp_cvc_multiap', 'refcat' : 'GAIA-DR2', 'zp_tolerance' : 0.1, 'overwrite' : True, 'color_const' : True, 'solar' : False}
catalog_type = 'FITS_LDAC_MULTIAPER'
file_index = fits_files.index(os.path.join(dataroot, 'fm221122-0192-e61.fits'))
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
for step in steps:
    pipeline_cls = PipelineProcess.get_subclass(step['name'])
    inputs = {f: pipeline_cls.inputs[f]['default'] for f in pipeline_cls.inputs}
    inputs.update(step['inputs'])
    print(f"  Performing pipeline step {step['name']}")
    pipe = pipeline_cls.create_timestamped(inputs)
#                self.stdout.write(f"  PK={pipe.pk} for {step['name']}")
    pipes.append(run_pipeline.message_with_options(args=[pipe.pk, step['name']], pipe_ignore=True))
runner  = pipeline(pipes).run()
steps
steps[2]
steps[2:3]
pipes = []
for step in steps[2:3]:
    pipeline_cls = PipelineProcess.get_subclass(step['name'])
    inputs = {f: pipeline_cls.inputs[f]['default'] for f in pipeline_cls.inputs}
    inputs.update(step['inputs'])
    print(f"  Performing pipeline step {step['name']}")
    pipe = pipeline_cls.create_timestamped(inputs)
#                self.stdout.write(f"  PK={pipe.pk} for {step['name']}")
    pipes.append(run_pipeline.message_with_options(args=[pipe.pk, step['name']], pipe_ignore=True))
runner  = pipeline(pipes).run()
Frame.objects.get(filename='fm221122-0192-e62.fits', frametype=Frame.NEOX_RED_FRAMETYPE)
frame = Frame.objects.get(filename='fm221122-0192-e62.fits', frametype=Frame.NEOX_RED_FRAMETYPE)
frame.__dict__
frame.delete()
pipes = []
for step in steps[2:3]:
    pipeline_cls = PipelineProcess.get_subclass(step['name'])
    inputs = {f: pipeline_cls.inputs[f]['default'] for f in pipeline_cls.inputs}
    inputs.update(step['inputs'])
    print(f"  Performing pipeline step {step['name']}")
    pipe = pipeline_cls.create_timestamped(inputs)
#                self.stdout.write(f"  PK={pipe.pk} for {step['name']}")
    pipes.append(run_pipeline.message_with_options(args=[pipe.pk, step['name']], pipe_ignore=True))
runner  = pipeline(pipes).run()
pipes = []
for step in steps[2:]:
    pipeline_cls = PipelineProcess.get_subclass(step['name'])
    inputs = {f: pipeline_cls.inputs[f]['default'] for f in pipeline_cls.inputs}
    inputs.update(step['inputs'])
    print(f"  Performing pipeline step {step['name']}")
    pipe = pipeline_cls.create_timestamped(inputs)
#                self.stdout.write(f"  PK={pipe.pk} for {step['name']}")
    pipes.append(run_pipeline.message_with_options(args=[pipe.pk, step['name']], pipe_ignore=True))
runner  = pipeline(pipes).run()
frames = Frame.objects.filter(filename__startswith='fm221122-0192')
for frame in frames:
    print(frame.filename, frame.frametype)
    
red_frames = Frame.objects.filter(filename__contains='-e62')
red_frames.count()
red_frames.delete()
