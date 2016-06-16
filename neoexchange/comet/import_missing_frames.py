#!/usr/bin/env python

import os
import sys
from glob import glob

from astropy.io import fits

sys.path.insert(0, os.path.join(os.getenv('HOME'), 'GIT/neoexchange/neoexchange'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'neox.settings'
import django
from django.conf import settings
django.setup()

from core.models import Frame, Block
from astrometrics.ephem_subs import LCOGT_domes_to_site_codes

datadir = os.path.join(os.getenv('HOME'), 'Asteroids', '67P', 'Pipeline2')
datadir = os.path.join(os.path.abspath(datadir), '')

block = Block.objects.get(pk=1)

print block
print datadir

fits_files = sorted(glob(datadir + '*e??.fits'))

for frame in fits_files:
    fits_file = os.path.basename(frame)
    raw_fits_file = fits_file.replace('e90', 'e00')
    print "%s->%s" % (fits_file, raw_fits_file)

    try:
        hdulist = fits.open(frame)
        header = hdulist[0].header
        hdulist.close()
        sitecode = LCOGT_domes_to_site_codes(header.get('siteid', None), header.get('encid', None), header.get('telid', None))
        frame_params = {  'midpoint' : header.get('date-obs', None),
                         'sitecode' : sitecode,
                         'filter'   : header.get('filter', "B"),
                         'instrument': header.get('instrume', None),
                         'filename'  : header.get('origname', None),
                         'exptime'   : header.get('exptime', None),
                         'frametype': Frame.SINGLE_FRAMETYPE,
                         'block'    : block,
                         'zeropoint' : header.get('l1zp', -99.0),
                         'fwhm'      : header.get('l1fwhm', None)
                     }
        print frame_params
        frame, frame_created = Frame.objects.get_or_create(**frame_params)
        print frame, frame.id, frame_created
    except IOError as e:
        print "Unable to open FITS catalog %s (Reason=%s)" % (frame, e)

    
