# Replicates core.models.frame.unpickle_wcs across every stored blob: b64decode -> pickle.loads -> WCS(header)
import sys, glob, pickle, base64, os, warnings, astropy
from astropy.wcs import WCS
warnings.simplefilter('ignore')
d='./wcs_pickles'
print(f"--- loading under astropy {astropy.__version__} / python {sys.version.split()[0]} ---")
for f in sorted(glob.glob(d+'/*.b64')):
    try:
        hdr = pickle.loads(base64.b64decode(open(f).read().encode()))
        w = WCS(hdr); n = len(hdr)
        sky = w.all_pix2world([[100.0, 100.0]], 1)[0]
        print(f"OK   {os.path.basename(f):<36} cards={n:<4} crval={[round(x,6) for x in w.wcs.crval]} pix(100,100)->{[round(x,6) for x in sky]}")
    except Exception as e:
        print(f"FAIL {os.path.basename(f):<36} {type(e).__name__}: {str(e)[:120]}")
