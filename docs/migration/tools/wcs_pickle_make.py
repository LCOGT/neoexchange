# Replicates core.models.frame.pickle_wcs: pickle an astropy Header (protocol 2), base64-encode.
import sys, pickle, base64, astropy
from astropy.io import fits
from astropy.wcs import WCS
src = 'neoexchange/photometrics/tests/banzai_test_frame.fits'
tag = sys.argv[1]
hdr = fits.getheader(src)
w = WCS(hdr)
out = {}
out['raw_header'] = base64.b64encode(pickle.dumps(hdr, protocol=2)).decode()
wh = w.to_header(); wh.insert(0, ("NAXIS", 2, "number of array dimensions")); wh.insert(1, ("NAXIS1", hdr.get('NAXIS1', 0), "")); wh.insert(2, ("NAXIS2", hdr.get('NAXIS2', 0), ""))
out['wcs_header'] = base64.b64encode(pickle.dumps(wh, protocol=2)).decode()
for k, v in out.items():
    open(f'./wcs_pickles/{k}_astropy{tag}.b64', 'w').write(v)
print(tag, 'astropy', astropy.__version__, 'python', sys.version.split()[0], 'crval', list(w.wcs.crval), 'written', list(out))
