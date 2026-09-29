# coding: utf-8
from core.models import Block,Body,SuperBlock, Frame
import os
from glob import glob
data_dir = os.path.join(os.sep,'apophis','eng','rocks','20210722','G22_263211087','Temp')
fits_catalogs = glob(data_dir + '/*e92.fits')
data_dir
get_ipython().system('ls -ltr /apophis/eng/rocks/20210722/G22_263211087/Temp')
for fits_catalog in fits_catalogs:
    header, table, cat_type = open_fits_catalog(fits_catalog)
    print(os.path.basename(fits_catalog), header['object'], header['siteid'], header['encid'], header['SEXDBLDC'])
    
from photometrics.catalog_subs import open_fits_catalog, get_fits_files
for fits_catalog in fits_catalogs:
    header, table, cat_type = open_fits_catalog(fits_catalog)
    print(os.path.basename(fits_catalog), header['object'], header['siteid'], header['encid'], header['SEXDBLDC'])
    
fits_catalogs
fits_catalogs = glob(data_dir + '/*e92_ldac.fits')
for fits_catalog in fits_catalogs:
    header, table, cat_type = open_fits_catalog(fits_catalog)
    print(os.path.basename(fits_catalog), header['object'], header['siteid'], header['encid'], header['SEXDBLDC'])
    
header
for fits_catalog in fits_catalogs:
    header, table, cat_type = open_fits_catalog(fits_catalog)
    print(os.path.basename(fits_catalog), header['object'], header['siteid'], header['encid'], header['SEXDBLDC'], header['SEXSATLV'], header['saturate'], header['maxlin'])
    
    
fits_catalog
fits_catalogs
fits_catalogs.sort()
fits_catalogs
fits_catalogs[-2]
fits_catalog = fits_catalogs[-2]
header, table, cattype = open_fits_catalog(fits_catalog)
header
get_ipython().system('less /apophis/eng/rocks/20210722/G22_263211087/Temp/sextractor_gps_ldac.conf')
get_ipython().run_line_magic('history', '')
blocks = Block.objects.filter(superblock__groupid__contains='shutter timing', block_start__gte='2021-07-21T00:00:00', block_end__lte='2021-07-21T12:00:00')
blocks
for block in blocks.order_by('block_start'):
    frames = Frame.objects.filter(block=block, frametype=Frame.BANZAI_LDAC_CATALOG)
    print(block.superblock.groupid, block.block_start, block.block_end, frames.count())
    #frames.delete()
    
for block in blocks.order_by('block_start'):
    frames = Frame.objects.filter(block=block, frametype=Frame.BANZAI_LDAC_CATALOG)
    print(block.superblock.groupid, block.block_start, block.block_end, frames.count())
    frames.delete()
    
    
import warnings
from astropy.wcs import FITSFixedWarning
warnings.simplefilter('ignore', category=FITSFixedWarning)
blocks = Block.objects.filter(superblock__groupid__contains='shutter timing', block_start__gte='2021-07-20T16:00:00', block_end__lte='2021-07-21T12:00:00')
for block in blocks.order_by('block_start'):
    frames = Frame.objects.filter(block=block, frametype=Frame.BANZAI_LDAC_CATALOG)
    print(block.superblock.groupid, block.block_start, block.block_end, frames.count())
    #frames.delete()
    
blocks = Block.objects.filter(superblock__groupid__contains='shutter timing', block_start__gte='2021-07-16T16:00:00', block_end__lte='2021-07-17T12:00:00')
for block in blocks.order_by('block_start'):
    frames = Frame.objects.filter(block=block, frametype=Frame.BANZAI_LDAC_CATALOG)
    print(block.superblock.groupid, block.block_start, block.block_end, frames.count())
    #frames.delete()
    
for block in blocks.order_by('block_start'):
    frames = Frame.objects.filter(block=block, frametype=Frame.BANZAI_LDAC_CATALOG)
    print(block.superblock.groupid, block.block_start, block.block_end, frames.count())
    frames.delete()
    
    
blocks = Block.objects.filter(superblock__groupid__contains='shutter timing', block_start__gte='2021-07-27T00:00:00', block_end__lte='2021-07-27T23:00:00')
for block in blocks.order_by('block_start'):
    frames = Frame.objects.filter(block=block, frametype=Frame.BANZAI_LDAC_CATALOG)
    print(block.superblock.groupid, block.block_start, block.block_end, frames.count())
    #frames.delete()
    
    
    
for block in blocks.order_by('block_start'):
    frames = Frame.objects.filter(block=block, frametype=Frame.BANZAI_LDAC_CATALOG)
    print(block.superblock.groupid, block.block_start, block.block_end, frames.count())
    frames.delete()
    
for block in blocks.order_by('block_start'):
    frames = Frame.objects.filter(block=block, frametype=Frame.BANZAI_LDAC_CATALOG)
    print(block.superblock.groupid, block.block_start, block.block_end, frames.count())
    #frames.delete()
    
    
    
blocks = Block.objects.filter(superblock__groupid__contains='shutter timing', block_start__gte='2021-07-26T12:00:00', block_end__lte='2021-07-27T10:00:00')
for block in blocks.order_by('block_start'):
    frames = Frame.objects.filter(block=block, frametype=Frame.BANZAI_LDAC_CATALOG)
    print(block.superblock.groupid, block.block_start, block.block_end, frames.count())
    #frames.delete()
    
blocks = Block.objects.filter(superblock__groupid__contains='shutter timing', block_start__gte='2021-07-26T12:00:00', block_end__lte='2021-07-27T18:00:00')
for block in blocks.order_by('block_start'):
    frames = Frame.objects.filter(block=block, frametype=Frame.BANZAI_LDAC_CATALOG)
    print(block.superblock.groupid, block.block_start, block.block_end, frames.count())
    #frames.delete()
    
get_ipython().system('pwd')
for block in blocks.order_by('block_start'):
    frames = Frame.objects.filter(block=block, frametype=Frame.BANZAI_LDAC_CATALOG)
    print(block.superblock.groupid, block.block_start, block.block_end, frames.count())
    #frames.delete()
    
blocks = Block.objects.filter(superblock__groupid__contains='shutter timing', block_start__gte='2021-07-26T12:00:00', block_end__lte='2021-07-27T04:00:00')
for block in blocks.order_by('block_start'):
    frames = Frame.objects.filter(block=block, frametype=Frame.BANZAI_LDAC_CATALOG)
    print(block.superblock.groupid, block.block_start, block.block_end, frames.count())
    #frames.delete()
    
Block.objects.get(request_number=2591043)
body_G24 = Body.objects.get(name='G24')
body_G24.__dict__
body_G24.id = None
body_G24.name = 'G15'
body_G24.__dict__
body_G24._state
body_G24._state = None
body_G24.save()
from django.forms import model_to_dict
body_G24 = Body.objects.get(name='G24')
model_to_dict(body_G24)
params = model_to_dict(body_G24)
params['id']
params['id'] = None
params['name'] = 'G15'
Body.objects.get_or_create(**params)
from core.frames import block_status
block_status(22158)
blocks = Block.objects.filter(superblock__groupid__contains='shutter timing', block_start__gte='2021-07-27T12:00:00', block_end__lte='2021-07-28T04:00:00')
for block in blocks.order_by('block_start'):
    frames = Frame.objects.filter(block=block, frametype=Frame.BANZAI_LDAC_CATALOG)
    print(block.superblock.groupid, block.block_start, block.block_end, frames.count())
    #frames.delete()
    
for block in blocks.order_by('block_start'):
    frames = Frame.objects.filter(block=block)
    print(block.superblock.groupid, block.block_start, block.block_end, frames.count())
    #frames.delete()
    
for block in blocks.order_by('block_start'):
    frames = Frame.objects.filter(block=block)
    print(block.superblock.groupid, block.block_start, block.block_end, frames.count())
    #frames.delete()
    
for block in blocks.order_by('block_start'):
    frames = Frame.objects.filter(block=block)
    print(block.superblock.groupid, block.block_start, block.block_end, frames.count())
    frames.delete()
    
    
get_ipython().run_line_magic('history', '')
daydirs = glob('/apophis/eng/rocks/20210806')
daydirs
gps_sats = Body.objects.filter(name__startswith='G',origin='L')
gps_sats
gps_sats.filter(name='G09')
gps_sats.filter(name='G30')
gps_sats = Body.objects.filter(name__startswith='G',origin='L')
gps_sats.filter(name='G30')
blocks = Block.objects.filter(superblock__groupid__contains='shutter timing', block_start__gte='2021-08-06T02:00:00', block_end__lte='2021-08-28T04:00:00')
blocks
for block in blocks.order_by('block_start'):
    frames = Frame.objects.filter(block=block)
    print(block.superblock.groupid, block.block_start, block.block_end, frames.count())
    #frames.delete()
    
    
    
for block in blocks.order_by('block_start'):
    frames = Frame.objects.filter(block=block)
    print(block.superblock.groupid, block.block_start, block.block_end, frames.count(), frames.filter(frametype=Frame.BANZAI_LDAC_CATALOG).count())
    #frames.delete()
    
gps_sats = Body.objects.filter(name__startswith='G',origin='L')
get_ipython().system('sync')
get_ipython().run_line_magic('history', '')
gps_sats = Body.objects.filter(name__startswith='G',origin='L')
gps_sats.filter(name='G14')
gps_sats.filter(name='G28')
get_ipython().run_line_magic('history', '')
