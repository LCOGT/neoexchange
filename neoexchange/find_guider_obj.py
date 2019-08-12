import os
from glob import glob
from datetime import datetime, timedelta
import warnings
from math import sqrt,log10

import astropy.units as u
from astropy.io import fits
from astropy.table import Table
from astropy.coordinates import SkyCoord, Angle
from astropy.utils.exceptions import AstropyDeprecationWarning
warnings.simplefilter('ignore', category = AstropyDeprecationWarning)
from astroquery.jplhorizons import Horizons

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "neox.settings")
from django.conf import settings
import django
django.setup()

from core.models import Body, Block, Frame, SourceMeasurement, CatalogSources
from core.frames import create_frame
from astrometrics.time_subs import datetime2mjd_utc

def get_header(catalog):
    fits_file = catalog.replace('.ecsv', '.fits')
    hdulist = fits.open(fits_file)
    header = hdulist[0].header
    header['RLEVEL'] = 91
    return header

def find_source(table, ref_pos, box_halfwidth_deg = 10/3600.0):

    ra_deg = ref_pos.ra.deg
    dec_deg = ref_pos.dec.deg
    ra_min = ra_deg - box_halfwidth_deg
    ra_max = ra_deg + box_halfwidth_deg
    box_dec_min = dec_deg - box_halfwidth_deg
    box_dec_max = dec_deg + box_halfwidth_deg
    dec_min = min(box_dec_min, box_dec_max)
    dec_max = max(box_dec_min, box_dec_max)
    mask1 = table['ra'] < ra_min
    mask2 = table['ra'] > ra_max
    mask3 = table['dec'] < dec_min
    mask4 = table['dec'] > dec_max
    status = mask1 | mask2 | mask3 | mask4

    sources = table[~status]
    min_sep = 180 * u.deg
    best_source = None
    for source in sources: 
        c1 = SkyCoord(source['ra'], source['dec'], unit=u.deg) 
        sep = c1.separation(ref_pos)
        if sep < min_sep:
            min_sep = sep
#            print("Found closer source", sep.to(u.arcsec))
            best_source = source
    return best_source, min_sep

def make_cat_source(source):
    catsrc_params = {
                        'obs_x' : source['XWIN_IMAGE'],
                        'obs_y' : source['YWIN_IMAGE'],
                        'obs_ra' : source['ra'],
                        'obs_dec' : source['dec'],
                        'obs_mag' : -2.5*log10(source['FLUX_AUTO']),
                        'err_obs_ra' : sqrt(source['ERRX2_WORLD']),
                        'err_obs_dec' : sqrt(source['ERRY2_WORLD']),
                        'err_obs_mag': 0.1,
                        'background': source['BACKGROUND'],
                        'major_axis': source['AWIN_IMAGE'],
                        'minor_axis': source['BWIN_IMAGE'],
                        'position_angle': source['THETAWIN_IMAGE'],
                        'ellipticity': source['ELLIPTICITY'],
                        'aperture_size': None,
                        'flags': source['FLAGS'],
                        'flux_max': source['FLUX_MAX'],
                        'threshold': None
                    }

    catsrc = CatalogSources(**catsrc_params)

    return catsrc

def make_source_measurement(body, frame, cat_source, persist=False):
    source_params = { 'body' : body,
                      'frame' : frame,
                      'obs_ra' : cat_source.obs_ra,
                      'obs_dec' : cat_source.obs_dec,
                      'obs_mag' : cat_source.obs_mag + frame.zeropoint,
                      'err_obs_ra' : cat_source.err_obs_ra,
                      'err_obs_dec' : cat_source.err_obs_dec,
                      'err_obs_mag' : cat_source.err_obs_mag,
                      'astrometric_catalog' : frame.astrometric_catalog,
                      'photometric_catalog' : frame.photometric_catalog,
                      'aperture_size' : cat_source.aperture_size,
                      'snr' : cat_source.make_snr(),
                      'flags' : cat_source.map_numeric_to_mpc_flags()
                    }
    source, created = SourceMeasurement.objects.get_or_create(**source_params)
    mpc_line = source.format_mpc_line()
    ades_psv_line = source.format_psv_line()
    if persist is not True:
        source.delete()
    return mpc_line, ades_psv_line

if __name__ == "__main__":
    target = '2019 OD'
    body = Body.objects.get(name=target)
    block = Block.objects.get(body=body,telclass='2m0')
    print(body.current_name(), block.superblock.groupid)
    print()
    print()
    datadir = os.path.join(settings.DATA_ROOT, '20190723', target.replace(' ', '_'), 'target_in_field')
    catalogs = glob(datadir + '/*.ecsv')
    catalogs.sort()

    mpc_lines = []
    for catalog in catalogs:
        header = get_header(catalog)
        frame = create_frame(header, block)
        frame.astrometric_catalog = 'GAIA-DR2'
        frame.zeropoint = 26.58
        frame.save()

        midpoint = datetime2mjd_utc(frame.midpoint) + 2400000.5
        print(frame.sitecode, frame.midpoint, midpoint)
        obj = Horizons(id=target, location=frame.sitecode, epochs=midpoint)
        ephem = obj.ephemerides()
        
        ra_deg = ephem[0]['RA']
        dec_deg = ephem[0]['DEC']
        ref_pos = SkyCoord(ra_deg, dec_deg, unit=u.deg)
        table = Table.read(catalog)
        best_source, min_sep = find_source(table, ref_pos)

        if best_source:
            print("{}    Predicted: {:.6f} {:.6f}".format(frame.midpoint.strftime("%Y-%m-%d %H:%M:%S"), ref_pos.ra.deg, ref_pos.dec.deg))
            print("Target found at: ({:.2f}, {:.2f}) {:.6f} {:.6f} @{:.1f}".format(best_source['XWIN_IMAGE'],
                best_source['YWIN_IMAGE'], best_source['ra'], best_source['dec'], min_sep.to(u.arcsec)))
            if  min_sep <= 1.0 * u.arcsec:
                catsrc = make_cat_source(best_source)
                mpc_line, ades_psv_line = make_source_measurement(body,frame,catsrc, persist=False)
                mpc_lines.append(mpc_line)
    print()
    for line in mpc_lines:
        print(line)
