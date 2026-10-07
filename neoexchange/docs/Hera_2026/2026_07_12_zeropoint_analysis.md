# Didymos 2026-07-12 — zeropoint cross-check analysis

Block **35906**, `coj2m002-ep07` (COJ 2 m / MuSCAT3 r′), 86 × 210 s frames (0058–0143), pixel scale 0.267″/px.
Notebook: `docs/Hera_2026/2026_07_12_photometry_local.ipynb`, section "Zeropoint cross checks" (cell index 43–44).
Analysis done 2026-10-05.

**Data sources:**
- DB `neoexchange-dev-copy`.
- NEOx frames under `/apophis/eng/rocks/Hera/20260712/`.
- PhotPipe reduction in `/apophis/tlister/Asteroids/65803_E10_20260712_rp/` (LOG, curve of growth, `.ldac.db`).
- PhotPipe table `lcogt_coj-PP_ep07_20260712_4253588_65803didymos_photometry.tab`.
- Target photometry `didymos_photometry/aper_p_Didymos*_712_*.ecsv`.

**Code:** line numbers refer to branch `pipelines` at `77ecc148` in this checkout. NEOx frames were reduced on
**apophis2**, which runs that branch plus an uncommitted patch captured in `docs/migration/apophis2/uncommitted.patch`
(MIGRATION_PLAN Q18). Where they differ, this document says which applies.

## Summary

1. **Conventions.** NEOx zeropoints are for 1 count/s and PhotPipe's for 1 count per exposure (+5.806 mag at 210 s).
   Neither is wrong. After correcting, PhotPipe − NEOx = −0.069 ± 0.020 mag.
2. **The remaining PhotPipe − NEOx difference is fully explained, with no model needed.**
   - NEOx fits its zeropoint with a **6 px** radius aperture (apophis2's `PHOT_APERTURES 12`).
   - PhotPipe uses **5 px** (`-PHOT_APERTURES 10.0`; "best-fit aperture radius: 5.0 (px)" in its LOG).
   - The 5 px/6 px flux ratio measured on each frame's stars predicts dZP with r = **0.995**. The residual is
     **+0.0053 ± 0.0020 mag**, which matches PhotPipe's PS1→SDSS r transformation for this field (median +0.0047).
3. **Bug: e93 frames carry BANZAI's e91 zeropoint, not the e92 calviacat one.** Confirmed on all 86 frames. The
   SExtractor `.bkgsub.fits` check image is written before `proc-zeropoint` updates `L1ZP`, and HOTPANTS copies that
   stale header into e93. This is the "smooth" orange series.
4. **The target photometry and its zeropoint use different apertures.** The e93 target photometry uses **5″**
   apertures (`perform_aper_photometry` works in arcsec). Measured from the stars on each frame:
   - **Now (BANZAI zeropoint):** Didymos is too bright by 0.034–0.055 mag (median 0.043). That is almost constant: it
     varies by only 0.020 mag peak-to-peak.
   - **After fixing item 3 alone (e92 zeropoint):** too bright by 0.089–0.270 mag (median 0.153), with a **0.181 mag
     peak-to-peak seeing-correlated** variation that would contaminate the lightcurve.
   Item 3 must not be fixed and the tables regenerated without also fixing the aperture mismatch.
5. **The committed `pipelines` branch can't run `proc-zeropoint`.** `processdata.py:511,523` pass `frame_filepath=`,
   but the committed signature takes `frame_filename`. Only apophis2's uncommitted patch makes this work (Q18,
   already planned).
6. **The excess scatter in the circulated PhotPipe lightcurve (χ²_red ≈ 3.5) is not a zeropoint problem (§6).**
   - **Trailing:** the frames were tracked sidereally, so Didymos trails **6.6 px** in a 5 px-radius aperture while
     the calibration stars are round. The extra loss (0.067–0.112 mag) does not cancel; it makes the magnitudes about
     0.09 mag too faint and varies with seeing. A PSF simulation agrees (0.09–0.10 mag at 1.44″). Rubin's
     SMTN-003 trailing-loss formula is an S/N loss, not a flux correction, and is tuned to Rubin's 2 × 15 s snaps,
     so it doesn't apply here.
   - **Field stars:** 19 frames have more than 0.02 mag of star flux in the aperture.
   - **Result:** fitting a seeing term and dropping those frames gives χ²_red ≈ 1.0.
7. **Aperture units and choice (§7).**
   - **NEOx's 4/5/8/13 radii are arcsec.** This is confirmed from the flux itself, so the notebook comparison tested
     15–49 px apertures (≥ 2.9 × FWHM) and never the S/N-optimal ~5 px.
   - **The arcsec unit comes from the original seeing-scaled default** (2.5 × `L1FWHM`). The management command
     exposes a fixed radius with no unit.
   - **PhotPipe's curve of growth is sound for round sources, but not by default for this trailed target.** It chose
     5 px and accepted a 0.058 mag target-versus-star differential loss that varies with seeing.

---

## 1. Zeropoint conventions

NEOx divides by exposure time before taking the magnitude, then adds the zeropoint:

```python
# photometrics/catalog_subs.py:1741
        new_table['obs_mag'] = -2.5 * np.log10(new_table['obs_mag'] / header_items['exptime'])
# photometrics/catalog_subs.py:1747
        new_table['obs_mag'] += header_items['zeropoint']
```

PhotPipe's `inst_mag` is `-2.5 log10(counts)` over the whole exposure: `mag = inst_mag + ZP` holds row by row. So:

```
ZP_PP = ZP_NEOx + 2.5 * log10(exptime)        # +5.806 mag for 210 s
```

| | Instrumental mag | ZP = mag giving… | Typical value, this block |
|---|---|---|---|
| NEOx `Frame.zeropoint` | `-2.5 log10(F / t)` | 1 count/s | ~24.80 |
| PhotPipe `ZP` | `-2.5 log10(F)` | 1 count/exposure | ~30.5 |

Per-second is the better convention to keep. It describes the telescope rather than the exposure, it matches BANZAI's
`L1ZP` and how NEOx applies it, and exposures of different lengths can be compared directly.

## 2. PhotPipe − NEOx: aperture size plus filter system

### What each pipeline did

| | NEOx (e92) | PhotPipe |
|---|---|---|
| Input image | `…-e92.fits` | `…-e91.fits` (pixel data **identical** to e92: `np.array_equal` on frame 0058) |
| Aperture radius for the zeropoint | **6 px** (1.60″) | **5 px** (1.335″) |
| Background for aperture photometry | SExtractor `BACKPHOTO_TYPE LOCAL`, thickness 24 | SExtractor `-BACKPHOTO_TYPE LOCAL` |
| Detection threshold | 1.2σ (apophis2 config) | 1.5σ, minarea 4 |
| Reference catalog | PS1 r (calviacat, `color_const=True`, `solar=False`) | PS1 transformed to **SDSS r (AB)** (`PANSTARRS_transformed`) |
| Aperture correction | none | none. The curve of growth only *chooses* the radius |

**PhotPipe evidence** (`/apophis/tlister/Asteroids/65803_E10_20260712_rp/LOG`):

```
622:  pp_extract.py: call Source Extractor as: sex -c .../setup/lcospec.sex  -PHOT_APERTURES 10.0  -BACKPHOTO_TYPE LOCAL ...
2662: pp_photometry.py: ==> best-fit aperture radius: 5.0 (px)
3108: pp_calibrate.py: derive zeropoint for catalog: ... based on PANSTARRS_transformed | ... 835 transformed to r (AB)
2020: pp_photometry.py: WARNING: frame ...-0066-e91.fits, large residual to HORIZONS position of 65803: 0.736568 arcsec; ignore this frame
2026: pp_photometry.py: WARNING: frame ...-0067-e91.fits, large residual to HORIZONS position of 65803: 0.814017 arcsec; ignore this frame
```

The last two lines explain why 0066 and 0067 are commented out of the table. `photometry_65803_Didymos__1996_GT_.dat`
in that directory is the source of the `.tab` used in the notebook, with identical numbers. The filenames in the `.tab`
were changed from `-e91.lda` to `-e92.fits` to allow the join. That is valid, because the pixels are identical.

PhotPipe's own `aperturephotometry_curveofgrowth.dat` (stars, fraction of flux within 21 px) gives 0.772 at 5 px and
0.841 at 6 px. So its 5 px zeropoint absorbs about 0.28 mag of aperture loss. It is self-consistent only because
Didymos is measured in the same 5 px aperture.

**PS1 → SDSS r transformation** (`~/git/photometrypipeline/catalog.py:1362`, Tonry et al. 2012):

```python
            r_sdss = (r - 0.001 + 0.004*(g-r) + 0.007*(g-r)**2)
```

For the 514 catalog stars in frame 0058's `.ldac.db` (median g−r = 0.66), r_SDSS − r_PS1 has median **+0.0047** and
mean +0.0066 (16–84 %: +0.003 … +0.012). A fainter catalog magnitude means a higher zeropoint, so this term alone
raises PhotPipe's zeropoint by about 0.005 mag.

### NEOx's aperture is 6 px, not the committed 5 px

The **committed** `photometrics/configs/sextractor_neox_ldac.conf:44` has `PHOT_APERTURES 10` (diameter). apophis2's
uncommitted copy has:

```
# docs/migration/apophis2/uncommitted.patch — sextractor_neox_ldac.conf
-DETECT_THRESH	3.0          ->  +DETECT_THRESH	1.2
-ANALYSIS_THRESH	3.0          ->  +ANALYSIS_THRESH	1.2
-PHOT_APERTURES	10           ->  +PHOT_APERTURES	12
```

**Independent check:** I re-measured stars on `e92.bkgsub.fits` with photutils at the catalog `XWIN/YWIN` positions
(`FLAGS==0`, `CLASS_STAR>0.8`, unsaturated, about 200–280 stars per frame) and compared with the catalog `FLUX_APER`.
On 15 frames spanning the night (FWHM_IMAGE 3.3–5.8 px), the ratio equals 1 at **6.01 px every time**.

### Model-free decomposition of dZP (84 frames)

For each frame, I measured the median 5 px/6 px flux ratio of the same stars. 2.5 log10(F₅/F₆) is the dZP expected
if the aperture were the *only* difference.

| Quantity | Value |
|---|---|
| Observed dZP = ZP_PP(per s) − ZP_NEOx | median −0.069, std 0.0197, range −0.129 … −0.038 |
| Predicted 2.5 log10(F₅/F₆) | median −0.076, range −0.134 … −0.043 |
| Correlation, observed vs predicted | **r = 0.995**, slope 0.981 |
| Residual: observed − predicted | **+0.0053 ± 0.0020** (range −0.002 … +0.010) |
| Correlation of residual with FWHM_IMAGE / with time | +0.22 / −0.05 |
| Expected PS1→SDSS term | **+0.0047** (median), +0.0066 (mean) |

The aperture difference explains 99 % of the dZP variance. The remaining 0.005 mag is the PS1→SDSS transformation,
and the 0.002 mag scatter is well below `ZP_sig` (~0.017). There is **no** evidence for colour-term, background or
centring differences between the two pipelines.

An earlier version of this analysis fitted Moffat curve-of-growth models against `Frame.fwhm`. Those numbers are
superseded. `Frame.fwhm` is 1.16× SExtractor's `FWHM_IMAGE` (median ratio), so the fitted radii and PSF shape were
only approximate. All numbers in this document now come from direct flux measurements.

**Parked:** an aperture-correction step in NEOx (Fix 5). PhotPipe doesn't do one either; it only uses the curve of
growth to choose the aperture.

## 3. Bug: e93 frames carry BANZAI's e91 zeropoint

The orange series in cell 43 ("5SNR aperture photometry ZP", the `ZP` column of `aper_p_Didymos5snr_712_06_13.ecsv`)
scatters by 0.020 mag, against 0.051 for the e92 calviacat zeropoint, and is less tied to seeing (r = −0.45 against
FWHM, compared with −0.88). It is not a zeropoint measured on the difference image. That can't be done, because the
stars are subtracted out. It is BANZAI's zeropoint, passed along by accident.

### Evidence: all 86 ep07 frames

| Check | Frames passing |
|---|---|
| e93 `L1ZP` == `e92.bkgsub.fits` `L1ZP` | 86 / 86 |
| e93 `L1ZP` == `e92.rms.fits` `L1ZP` | 86 / 86 |
| e93 `L1ZP` == `L1ZP` in the `-e91_ldac.fits` `LDAC_IMHEAD` (BANZAI's header) | 86 / 86 |
| e93 `L1ZP` == DB `-e91_ldac.fits` Frame zeropoint (`zeropoint_src='BANZAI'`) | 86 / 86 |
| e93 `L1ZP` == DB e93 `Frame.zeropoint` | 86 / 86 |
| ECSV `ZP` == e93 `L1ZP` | 86 / 86 |
| e93 `L1ZP` ≠ e92 `L1ZP` | 86 / 86 |
| `e92.bkgsub.fits` older than `e92.fits` | 86 / 86 |
| CRVAL/CRPIX/CD identical across e92, bkgsub and e93 (WCS **not** stale) | 86 / 86 |
| e93 `PHOTNORM = 'i'` (HOTPANTS scaled to the science image) | 86 / 86 |

**Example, frame 0058.** The DB `PipelineProcess` IDs are 1599208–1599212, run on 2026-07-13 between 20:56 and 21:13
UTC.

| File | `L1ZP` | `L1ZPERR` | `L1ZPSRC` | mtime (PDT) |
|---|---|---|---|---|
| `e92.fits` | 24.78856 | 0.0107 | `py_zp_cvc-V0.2.1` | 14:13:05 |
| `e92.bkgsub.fits` / `.rms.fits` | **24.90759** | 0.0060 | — | 14:07:19 |
| `e93.fits` | **24.90759** | 0.0060 | — | 15:53:22 |

The zeropoint process logged `New zp=-0.11902698…`, and `update_zeropoint` adds it to the zeropoint already in the
header (`catalog_subs.py:1914`): 24.90759 − 0.11903 = 24.78856. So the e92 zeropoint is BANZAI's plus the calviacat
correction. The e93 file kept the uncorrected BANZAI value.

### How it happens

**Step 1:** the check images are written before the zeropoint step runs.

```python
# core/management/commands/run_pipeline.py — per-frame step order
115:  'proc-extract'     (on e91)
123:  'proc-astromfit'   (refitted WCS written into e92)
130:  'proc-extract'     (on e92 -> e92_ldac + .rms/.bkgsub/.bkgd/.apers check images)
138:  'proc-zeropoint'   (updates L1ZP in e92.fits and e92_ldac.fits only)
```

```python
# pipelines/processdata.py:210-212, 217
        if dia is True:
            # Options needed for image subtraction
            checkimage_types = ['BACKGROUND_RMS', "-BACKGROUND", "BACKGROUND", "APERTURES"]
        ...
        status, new_ldac_catalog = run_sextractor_make_catalog(configs_dir, dest_dir, fits_file, checkimage_type=checkimage_types, catalog_type=catalog_type)
```

SExtractor copies the e92 header *as it stands at that moment* into the check images. That header already has the
refitted WCS but still has BANZAI's `L1ZP`. `proc-zeropoint` then rewrites only:

```python
# pipelines/processdata.py:515, 519
                    status, new_fits_header = updateFITScalib(header, fits_filepath, update_frame_type)
                    status, new_fits_header = updateFITScalib(header, catfile, update_catalog_type)
```

**Step 2:** HOTPANTS takes the stale `.bkgsub.fits` as its input image and copies its header into the output.

```python
# photometrics/external_codes.py:399
    sci_bkgsub = os.path.join(dest_dir, os.path.basename(sci).replace(".fits", ".bkgsub.fits"))
# photometrics/external_codes.py:456
    options = f'-inim {sci_bkgsub} -tmplim {aligned_ref} -outim {output_diff_image} ' \
```

The options include `-n i`, which normalises the difference image to the photometric scale of the *science* image.
The e92 zeropoint is therefore the correct one for e93. Only the header copy is wrong.

**Step 3:** `updateFITSdia` changes only the reduction level and recipe.

```python
# photometrics/external_codes.py:1685-1686
        header['RLEVEL'] = new_red_level
    header['PPRECIPE'] = 'NEOEXCHANGE DIA'
```

**Step 4:** the e93 `Frame` record is created from that header.

```python
# core/views.py:3608, 3612, 3614  (run_hotpants_subtraction)
        status, header = updateFITSdia(hotpants_filepath)
            neox_header = get_catalog_header(header, 'HOTPANTS')
                num_new_frames = make_new_catalog_entry(hotpants_filepath, neox_header, block, Frame.NEOX_SUB_FRAMETYPE)
```

**Step 5:** the target photometry uses that DB value.

```python
# photometrics/external_codes.py:1875, 1906, 1909  (single_frame_aperture_photometry)
    frame = Frame.objects.get(filename=fits_filename)          # the e93 Frame
        source_flux['ZP'] = frame.zeropoint
            source_flux['mag'] = -2.5*np.log10(source_flux['aperture_sum']) + frame.zeropoint
```

The apophis2 uncommitted patch does not touch `determine_hotpants_options`, `updateFITSdia` or
`run_hotpants_subtraction`. Its only `external_codes.py` change is a debug print in `run_scamp`. So the bug is in both
the committed and the production code.

**Why the BANZAI zeropoint is smoother:** compared with the zeropoint a 5″ aperture would need (measured below), the
BANZAI zeropoint is lower by a nearly constant 0.043 mag (std 0.005). It therefore behaves like a zeropoint for a large,
nearly-total-flux aperture, plus a constant offset. That offset could be BANZAI's reference catalog or filter system,
or residual aperture loss. I haven't checked BANZAI's photometry settings, so the two can't be separated here.

## 4. The target aperture and the zeropoint aperture don't match

`single_frame_aperture_photometry` takes `aperture_radius` in **arcsec**:

```python
# photometrics/external_codes.py:1877-1878, 1892
    if aperture_radius == None:
        aperture_radius = 2.5*FWHM
    source_aperture = SkyCircularAperture(positions, r = aperture_radius*u.arcsec)
```

The `aper_p_Didymos*` ECSV columns are exactly the ones written by `perform_aper_photometry` (`core/views.py:5185-5200`),
so their 13/8/5/4 radii are **arcsec**: 5″ is 18.7 px. `2026_07_12_photometry_summary.md` §1 labels them "px" and
needs correcting.

A zeropoint fitted with a fixed aperture absorbs that aperture's flux loss, which only cancels if the target is
measured with the same aperture. The bias below is measured directly. For each frame I compared the median flux of
the same stars in a 5″ (18.7 px) and a 6 px aperture on `e92.bkgsub.fits`, which gives the zeropoint a 5″ aperture
would need. I then compared that with the zeropoint actually applied. HOTPANTS `-n i` puts e93 on the e92 scale, so
the e92 stars apply.

| Zeropoint applied to the 5″ target aperture | Too bright by: median | range | peak-to-peak | Correlation with FWHM |
|---|---|---|---|---|
| BANZAI, **current e93 tables** | **0.043** | 0.034–0.055 | 0.020 | −0.40 |
| e92 NEOx 6 px, **after fixing §3 only** | **0.153** | 0.089–0.270 | **0.181** | **+0.93** |
| Same aperture for target and zeropoint | 0 | — | — | — |

- **Current tables:** they are offset by about 0.04 mag but nearly flat. Relative lightcurve shapes are only slightly
  affected (≤ 0.02 mag), but absolute magnitudes are too bright.
- **Correcting the zeropoint without the aperture:** this would add a 0.18 mag peak-to-peak trend that follows seeing.
  Seeing changes slowly through the night, so that trend could easily be mistaken for rotational variation.

An earlier, model-based version of this table (0.014–0.110 now, and 0.063–0.316 after a §3-only fix) is superseded by
these measured values.

## 5. The committed `pipelines` branch can't run `proc-zeropoint`

```python
# photometrics/catalog_subs.py:1928  (committed)
def update_frame_zeropoint(header, ast_cat_name, phot_cat_name, frame_filename, frame_type):
# pipelines/processdata.py:511, 523  (committed since 6a3c3a89, 2023-09-16)
                    frame = update_frame_zeropoint(header, ast_cat_name, phot_cat_name, frame_filepath=fits_filepath, frame_type=Frame.NEOX_RED_FRAMETYPE)
                    frame_cat = update_frame_zeropoint(header, ast_cat_name, phot_cat_name, frame_filepath=catfile, frame_type=Frame.BANZAI_LDAC_CATALOG)
```

`inspect.signature(...).bind(...)` fails, so on the committed code this raises `TypeError` at line 511, before
`updateFITScalib`. The production run succeeded: the e92 Frame has `photometric_catalog='PS1'`, `rms_of_fit` and
`nstars_in_fit` set, and the header has `L1ZPSRC`. That is because apophis2's uncommitted patch changes the signature to
`frame_filepath`. In turn, the patched signature breaks the committed `catalog_subs.py:2078,2081` callers, which still
pass `frame_filename=`.

This is Q18, planned as change (2) of the `prep/apophis2-recovery` branch. Anyone re-running this reduction from a
non-apophis2 checkout will hit it. They would also get 5 px instead of 6 px apertures and 3σ instead of 1.2σ detection
thresholds, which shifts every zeropoint.

## 6. Excess scatter in the circulated PhotPipe lightcurve

**Short answer:** the zeropoint findings above do **not** cause it. The same underlying issue, a fixed small aperture
whose flux loss depends on seeing, does, together with field-star contamination.

- **Zeropoint ruled out:** PhotPipe's zeropoint agrees with NEOx's to 0.002 mag rms once aperture size and filter
  system are allowed for (§2). PhotPipe's `ZP_sig` is the scatter of individual calibration stars
  (`pp_calibrate.py:360`: `sigma = np.sqrt(var + np.mean(residuals_sig))`), not the error on the mean zeropoint
  (~0.001 for ~500 stars). Adding it to every point (`sig = hypot(in_sig, ZP_sig)`) *inflates* the error bars.

### Size of the excess

84 frames, excluding 0066 and 0067. The model is a 4th-order Fourier series at P = 2.2600 h plus a linear term.

| | rms resid | χ²_red (PP `sig`) | χ²_red (`in_sig` only) | extra noise needed |
|---|---|---|---|---|
| PhotPipe as circulated | 0.055 | 3.48 | 5.13 | 0.048 |
| + a linear seeing term (fitted jointly) | 0.045 | 2.34 | 3.47 | 0.036 |
| + drop 19 frames with field-star contamination > 0.02 mag | **0.030** | **1.03** | 1.49 | 0.014 |

The point-to-point scatter is 0.040 (χ² of successive differences 1.6), so most of the excess is correlated over many
frames rather than frame-to-frame noise.

### Cause 1: Didymos is trailed and the stars are not, so the aperture loss doesn't cancel

The frames were tracked sidereally: `SRCTYPE='EXTRASOLAR'`, `RATRACK = DECTRACK = 0`, `L1ELLIP` = 0.09. Didymos
moved 0.505″/min at PA 273°, which is **1.77″ = 6.6 px per 210 s exposure**. That is longer than PhotPipe's 5 px
aperture radius and comparable to the FWHM. The zeropoint comes from round stars in the same 5 px aperture, so it
absorbs the stars' aperture loss but not the target's extra trail loss.

- **Trail loss, measured per frame:** I averaged each frame's own star fluxes in 5 px apertures stepped along the
  6.6 px trail. The trailed target loses **0.067–0.112 mag more** than a star (median 0.092), and the amount tracks
  seeing (r = 0.97 with FWHM_IMAGE).
- **The circulated PhotPipe magnitudes are therefore too faint by about 0.09 mag.** This is confirmed independently:
  my own photometry of Didymos on e92, with the aperture correction for each radius measured from the stars, is
  0.069 / 0.079 / 0.086 mag brighter at 8 / 10 / 12 px than at 5 px.
- **The residuals follow seeing:** r = +0.51 against trail loss and +0.55 against FWHM. In 6-frame bins they run from
  −0.06 in the best seeing (FWHM 3.5–4.0 px, frames 0096–0107) to +0.07 in the worst (5.4–5.7 px, frames 0132–0143).
- **Aperture-dependence test:** I re-measured Didymos at 5–12 px, each radius calibrated with the e92 zeropoint plus
  the star-measured aperture correction. My 5 px values reproduce PhotPipe exactly (median difference 0.000).

  | Radius | Residual–FWHM correlation | Slope (mag per px of FWHM) |
  |---|---|---|
  | 5 px | +0.54 | 0.044 |
  | 8 px | +0.29 | 0.033 |
  | 10 px | +0.07 | 0.013 ± ~0.02 |

  The correlation weakens as the aperture grows, as an aperture effect should. Larger apertures are not a remedy,
  though: χ²_red rises from 4.9 to 45 as they pick up field stars and sky.
- **Caveat:** the fitted seeing coefficient (0.048–0.054 mag/px) is about 3–4× what the trail loss alone predicts
  (~0.013 mag/px between 3.3 and 6.2 px FWHM). The rest is either another seeing-dependent aperture effect (centroiding
  a faint trailed source, or the local-background annulus) or partly a coincidence with real variability. Seeing was
  worst at the start and end of the night, where a mutual event or other slow signal could sit. One night can't
  separate these.

### Cross-check: simulated trail loss, and the Rubin SMTN-003 formula

*Added 2026-10-07.*

**Rate units:** 1°/day = 2.5″/min = 150″/h. Didymos moved **0.505″/min = 0.202°/day**, so the trail is
0.505 × 210/60 = 1.77″ per 210 s exposure. The trail length relative to seeing is

x = v[″/min] · T[s] / (60 θ[″]) = v[°/day] · T[s] / (24 θ[″])

which is **1.23** here (θ = 1.44″).

**Simulated aperture loss** (`aperture_trail_loss()` below): a PSF smeared along a 1.77″ trail. Each entry is the
extra loss of the trailed target relative to a star in the same circular aperture (mag). The ranges cover a
double-Gaussian PSF and Moffat profiles with β = 2.5 and 4.

| FWHM | 5 px (1.33″) | 8 px (2.13″) | 12 px (3.19″) |
|---|---|---|---|
| 1.0″ | 0.06–0.07 | ≤ 0.012 | ≤ 0.002 |
| 1.44″ | 0.09–0.10 | 0.012–0.023 | ≤ 0.005 |
| 1.7″ | 0.09–0.11 | 0.022–0.028 | ≤ 0.006 |

- **Matches the measurement:** at 1.44″ this agrees with the 0.092 mag measured above from each frame's own stars.
- **Seeing dependence:** it reproduces the loss rising with seeing at 5 px.
- **Large apertures:** it confirms the loss is negligible by 12 px.
- **PhotPipe's curve of growth:** the 0.058 mag gap from PhotPipe's curve of growth (§7) is low by comparison, which
  supports the explanation that its star sample is too loose.

**SMTN-003 / `rubin_sim` `calc_trailing_losses`:**
[SMTN-003](https://smtn-003.lsst.io/) gives

dmag = 1.25 log10(1 + a x²/(1 + b x))

with a_trail = 0.761, b_trail = 1.162 and a_det = 0.420, b_det = 0.003.

- **Provenance:** the constants are fitted (`curve_fit`) to simulations in the technote's own
  `Trailing Losses.ipynb` (repo `lsst-sims/smtn-003`). They do not come from Vereš et al. That paper is
  [2012, PASP 124, 1197](https://arxiv.org/abs/1209.6106), not 2015, and gives an analytic trailed-Gaussian model
  for trail fitting.
- **What they measure:** they are **S/N losses, not flux losses.**
  - `dmag_trail` = 1.25 log10(n_eff,trail / n_eff,star). That is the sky-limited S/N penalty at S/N = 5 for an
    *optimal, trail-matched* measurement that captures all the flux.
  - `dmag_detect` is the drop in the peak of a stellar-PSF matched-filter image: Rubin's detection-threshold loss.
  - **Neither is a correction to apply to magnitudes.** The quantity that biases a lightcurve is the
    aperture-flux loss in the table above.
- **General:** the x scaling and the functional form. The pixel scale cancels, since the simulation is unpixelised
  on a 0.01″ grid.
- **Rubin-specific:**
  - **Snaps:** 2 × 15 s with a 2–4 s gap, fitted as if T = 30 s, which makes the trail 7–13% longer than v·T.
  - **PSF:** a double Gaussian approximating von Kármán.
  - **Seeing:** 0.7–1.2″ only.
  - **Fit range:** 0.02–10°/day (0.05–25″/min), i.e. x ≈ 0–17. That is dominated by long trails, so the two-parameter
    form overestimates at x ≲ 1.5.
- **Reproduced:** with their setup, my refit gives a = 0.634, b = 0.935. That agrees with their curve to 0.01 mag
  for x ≥ 2, but the published constants come out 0.025–0.03 mag high at x ≈ 1.
- **Didymos's S/N loss (x = 1.23):**

  | Model | S/N loss (mag) |
  |---|---|
  | SMTN-003 constants | 0.211 |
  | Their setup, simulated directly | ≈ 0.19 |
  | Single continuous exposure, double Gaussian | 0.15 |
  | Single continuous exposure, Moffat β = 2.5–4 | 0.12–0.14 |

  For a single LCO exposure, the published constants overstate the S/N loss by roughly 40–75% at this x.

### Cause 2: field stars in the aperture

The field was tracked sidereally, so the stars stay put while Didymos moves across them. I measured the star flux
falling in the trailed aperture's position on a frame where Didymos is elsewhere (0143 for early frames, 0058 for late
ones).

- **Extent:** 28 of 84 frames have more than 0.01 mag of contamination, 12 more than 0.03, with a maximum of 0.13 mag.
- **Matches the outliers:** the most negative (too bright) residuals, 0099 (−0.145), 0092 (−0.133) and 0091 (−0.095),
  have 0.11, 0.085 and 0.08 mag of contamination.
- **PhotPipe's flags don't catch it:** the correlation between residual and SExtractor flag > 0 is +0.01.

This is what DIA (e93) is for. The current e93 tables use 4–8″ apertures, though, and are 2–5× noisier than PhotPipe
(median error 0.06–0.15 mag), so they can't yet confirm a 0.05 mag effect.

### Recommendations for the circulated results

- **Absolute magnitudes:** the circulated PhotPipe magnitudes are about 0.09 mag too faint (trail loss) and carry a
  seeing-correlated systematic of order ±0.05 mag. Treat slow features that coincide with seeing changes (start and
  end of 2026-07-12) with suspicion.
- **Error bars:** `ZP_sig` adds about 0.017 mag of correlated, not random, error to each point. Once the systematics
  above are removed, `in_sig` plus a small term is closer to the true random error.
- **Re-reduction:** use either a trail-matched aperture (an elongated aperture along the motion, or an aperture
  correction from stars synthetically trailed by the measured 6.6 px, as done here), or rate-tracked observations.
  Use DIA, measured with a small aperture matched to its zeropoint aperture, to remove field stars.

## 7. Aperture units and aperture choice

*Added 2026-10-07.*

### Why `perform_aper_photometry` works in arcsec

The arcsec unit was coherent in the first version and broke once fixed radii were added.

- **First version** (`0cb8dfcc`, 2024-08, intern): there was no radius argument. The radius was `2.5 * header['fwhm']`,
  and that FWHM is BANZAI's `L1FWHM`, in arcsec (`Frame.fwhm` is too). The target position is the ephemeris RA/Dec,
  so `SkyCircularAperture(..., r=aperture_radius*u.arcsec)` (`external_codes.py:1892`) needs no pixel conversion and
  scales with seeing. That much is defensible.
- **`d4e0f01d`** (2024-09) added a fixed `aperture_radius` override. It inherited the arcsec unit, which the docstring
  states, and gave up the seeing scaling.
- **`pipeline_aper_photometry.py`** (`2e92b8ff`/`9392f35b`, 2026-07) exposes the radius as a bare positional float,
  with help text "Define aperture radius for photometry" and no unit. Radii chosen in pixel terms were silently
  applied as arcsec.
- **Dead code with mixed units:** the `background_subtract=True` branch builds a pixel-unit `CircularAnnulus` centred
  on `(ra, dec)` in degrees. It is off by default, but it is wrong.

### The `aper_p_Didymos*` radii are arcsec: confirmed from the flux

§4 inferred the unit from the code. The tables confirm it independently. These are median target sums over the same
86 e93 frames (`Frame.fwhm` 1.10–1.84″, median 1.40″):

| Radius | As arcsec | As px | Median sum (counts/s) | Median S/N | Arcsec model |
|---|---|---|---|---|---|
| 4 | 15.0 px | 1.07″ | 73.3 | 16.9 | 73.3 (fitted) |
| 5 | 18.7 px | 1.34″ | 73.5 | 13.3 | 71.5 |
| 8 | 30.0 px | 2.14″ | 62.5 | 7.2 | 63.5 |
| 13 | 48.7 px | 3.47″ | 41.1 | 2.7 | 42.2 (slope fitted) |

- **Pixel radii don't fit:** for a 1.4″ PSF, going from 1.07″ to 1.34″ should add about 8% of the flux. The sums are
  flat from 4 to 5 and then fall.
- **Arcsec radii fit:** a model of constant flux (76.6) plus a uniformly negative difference-image background
  (−0.20 counts/s per arcsec² × π r²) reproduces every radius to within about 2.
- **All four radii are far larger than the PSF.** The smallest, 4″, is about 2.9 × FWHM. The comparison measured how
  much residual background and noise each aperture took in, not how much target flux it caught.
- **The S/N-optimal radius was never tried.** That is about 1 × FWHM ≈ 1.4″ ≈ 5 px, which is what the notebooks
  thought they were testing.
- **The notebooks' own labels are wrong:** their print statements say "aperture radius at 13 pixels" and "r =5 px"
  (`2026_07_12_photometry.ipynb` cells 9 and 13; `_local` cells 17 and 21).

### PhotPipe's curve of growth: sound, with caveats

Read from `~/git/photometrypipeline/pp_photometry.py` (`8514d04`) and checked against this night's LOG and
`aperturephotometry_curveofgrowth.dat`.

**How PhotPipe picks the aperture:**
- **Radii:** 20 **pixel** radii from `linspace(aprad_range)` (`:382`), 2–21 px for `LCOMUSCEP07`.
- **Target curve:** the nearest source within `pos_epsilon = 0.5″` of Horizons in each frame (`:163-182`). Frames
  0066 and 0067 were dropped at 0.74″ and 0.81″. Each frame's curve is divided by its own maximum, and the median is
  taken over frames (`:211`).
- **Star curve:** the **first 50 rows** of each LDAC with `FLAGS ≤ 3` (`:188-192`). Those rows are in SExtractor's
  extraction order, not sorted by brightness. There is no S/N, isolation or star/galaxy cut, and flags 1–2 (blended,
  deblended) pass. The curve is the median over stars × frames (`:220`).
- **Criterion** (`:237-270`, `_pp_conf.py:182-183`): the smallest radius where both curves exceed 0.7 and they agree
  within 0.05 in normalised flux. It computes S/N curves but never uses them in the choice.
- **Application:** one radius, fixed in **pixels**, for every frame, the target and the calibration stars alike
  (`APRAD` header, `:330-336`). There is no aperture correction, and trailing isn't modelled.
- **Minor upstream bug:** the output's `n_target` and `n_bkg` (`:279-280`) report the number of apertures, not
  the number of frames or sources.

**What it chose here:** "best-fit aperture radius: 5.0 (px)". That is 1.33″, about 0.9 × FWHM (1.44″ `L1FWHM`), which
is close to S/N-optimal.

| r (px) | Stars | Didymos | Target − stars | As mag |
|---|---|---|---|---|
| 4 | 0.660 | 0.611 | −0.049 | 0.084 |
| **5** | **0.772** | **0.732** | **−0.040** | **0.058** |
| 8 | 0.910 | 0.894 | −0.015 | 0.019 |
| 12 | 0.953 | 0.951 | −0.002 | 0.002 |
| 21 | 0.995 | 0.986 | −0.009 | — |

- **Didymos's curve lies below the stars' out to about 12 px (3.2″).** That is the signature of the 6.6 px trail
  (§6). The criterion accepted a 0.058 mag differential loss at 5 px. In general, a 0.05 margin at the 0.7 level
  allows up to about 0.07 mag.
- **The curve hasn't converged at 21 px (5.6″).** The star curve still rises from 0.982 to 0.995 between 20 and
  21 px. "Fraction" therefore means the fraction of the flux inside 5.6″, not of the total.
- **Discrepancy with §6:** the curve's 0.058 mag at 5 px is smaller than §6's synthetic trail loss of 0.092 mag. A
  likely cause is the unselective star sample: faint, blended and extended sources have broader curves of growth,
  which pull the star curve down and narrow the gap. A median of normalised curves is also not a flux ratio. *Not
  verified.* Either way, the curve of growth independently confirms a trail loss of at least about 0.06 mag at 5 px.
- **Config provenance:** the `LCOMUSCEP07` entry this run used (`aprad_range [2, 21]`, `secpix 0.266`) is an
  **uncommitted local addition** in `~/git/photometrypipeline/setup/telescopes.py`. It also labels this COJ data
  `LCOGT(OGG)/MUSCAT`; the observatory code, E10, is correct.

**Verdict:**
- **For round sources in stable seeing, the method is reasonable.** The target and stars share one aperture, so the
  stars' aperture loss cancels in the zeropoint.
- **For a sidereally tracked, trailed target, it is not safe by default.** It accepts a few-percent differential loss,
  and because the pixel aperture is fixed while seeing changes, that loss varies through the night. It does not
  calibrate out (§6).
- **Two remedies:** a radius ≳ 1.5–2 × the night's worst FWHM plus half the trail length (`-fixed_aprad`, at some
  cost in S/N), or a per-frame trail-aware aperture correction (Fix 11).
- **Not comparable with NEOx yet:** NEOx's 4–13″ results can't be compared with PhotPipe's 5 px until the NEOx side is
  re-run in pixel or FWHM-scaled radii (Fixes 4 and 16).

## 8. Minor observations

- **Multi-aperture comment** (only affects `-ef` frames): `processdata.py:657-658` says "diameter=5"" for
  `inst_mag[0:, 4]`. Index 4 in `sextractor_neox_ldac_multiaper.conf:52` is `22.00` px diameter, which is inserted into
  a 1″–10″ radius sequence. The apophis2 patch also changes the related `flux_aper_index`/`aper_scaling` in
  `get_or_create_CatalogSources` (Q20).
- **Magnitude error:** `single_frame_aperture_photometry` computes `magerr` from the aperture-sum error only
  (`external_codes.py:1912`). `ZP_sig` is stored but not added in quadrature.
- **FWHM definitions differ:** `Frame.fwhm` is 1.16× SExtractor `FWHM_IMAGE`, and PhotPipe's `FWHM"` column is
  different again (1.85″ for 0058, against 1.44″ `L1FWHM`). Don't mix them when modelling apertures.
- **Notebook cell 43:** already fixed. `phot_times` now comes from `merged_table` after sorting by `julian_date`.

---

## Fixes

### Code

- [ ] **Fix 1 — copy the e92 calibration into e93.** In `run_hotpants_subtraction` (`core/views.py:3575`), which
  already has the `sci` (e92) path, or in `updateFITSdia(fits_file, sci_file=None)` (`external_codes.py:1665`): after
  HOTPANTS, copy the photometric-calibration keywords from the **e92** header into the e93 header and `.rms.fits`,
  *before* `get_catalog_header`/`make_new_catalog_entry`. The keywords are those `updateFITScalib` writes
  (`external_codes.py:1592-1600`): `L1ZP`, `L1ZPERR`, `L1ZPSRC`, `L1PHTCAT`, plus the colour keywords from
  `banzai_ldac_catalog_mapping`. Add a test that checks e93 `L1ZP` == e92 `L1ZP`. This is valid because of HOTPANTS
  `-n i`; if that option changes, so must this.
- [ ] **Fix 2 — keep the check images in sync.** After `proc-zeropoint` (`processdata.py:515`), also run
  `updateFITScalib` on `.bkgsub.fits` and `.rms.fits`. Defence in depth; Fix 1 is the primary fix.
- [ ] **Fix 3 — `update_frame_zeropoint` signature.** Part of the planned `prep/apophis2-recovery` change (2): adopt
  `frame_filepath`, tolerate bare filenames, update `catalog_subs.py:2078,2081` and the tests.
- [ ] **Fix 4 — match the target aperture to the zeropoint aperture.** **Must land with or before Fix 1 and the data
  repair.** Choose one:
  - (a) Measure Didymos on e93 with the zeropoint's aperture: 6 px = 1.602″ here, or in general
    `PHOT_APERTURES/2 × pixscale`. Simplest; it is what PhotPipe does (with 5 px).
  - (b) Seeing-scaled apertures (k × FWHM) for both stars and target, which needs multi-aperture catalogs.
  - (c) Aperture correction from a curve of growth (Fix 5).

  Whichever is chosen, `perform_aper_photometry` should record the zeropoint aperture it assumed.
- [ ] **Fix 5 (parked) — aperture correction.** `FITS_LDAC_MULTIAPER` catalogs already exist but `run_pipeline.py:95`
  only selects them for `-ef` frames. The star-flux-ratio method used in §2 and §4 is a working prototype: median
  ratio of bright, isolated, unsaturated stars between two apertures, measured per frame.
- [ ] **Fix 6 — commit the apophis2 config.** Review and commit the `sextractor_neox_ldac.conf` tuning
  (`PHOT_APERTURES 12`, `DETECT/ANALYSIS_THRESH 1.2`; Q20, Tim's to commit), so reductions are reproducible from any
  checkout. Consider writing the aperture into the e92 header (e.g. `L1ZPAPER`) during `proc-zeropoint`, so it is
  recorded with the data rather than inferred.
- [ ] **Fix 7 (minor):** correct the index-4 comment and the multiaper aperture list, and add `ZP_sig` in quadrature to
  `magerr` (or document that it is left out).

### Data repair (after Fix 1 **and** Fix 4)

- [ ] **Fix 8:** a management command, e.g. `fix_e93_zeropoints --block <id> | --date <YYYYMMDD> [--dry-run]`. For
  each e93 `Frame`, find the e92 `Frame` (`-e93` → `-e92`). Copy `zeropoint`, `zeropoint_err`, `zeropoint_src` and the
  colour fields, and patch the same keywords in the e93 FITS and `.rms.fits` headers. Report frames whose e92 has no
  good zeropoint rather than skipping them silently. Run it on every DIA-processed block, not only 35906.
- [ ] **Fix 9:** regenerate the `aper_p_Didymos*.ecsv` tables only after Fix 4. Applying the corrected e92 zeropoint
  to the existing 5″ apertures would introduce a 0.09–0.27 mag (0.18 peak-to-peak) seeing-correlated bias (§4).

### Documentation

- [ ] **Fix 10:** in `2026_07_12_photometry_summary.md` §1, change the aperture radii from "px" to "arcsec" (13/8/5/4″).
  Do the same for the notebooks' "pixels"/"px" print labels (§7).

### Moving-target photometry (§6)

- [ ] **Fix 11 — trail-aware aperture correction.** For sidereally tracked frames, correct each frame for the
  target's extra trail loss: either an aperture correction from the frame's own stars smeared synthetically along the
  measured trail (the method in §6, `trail_loss()` below), or an elongated aperture along the motion. The rate, PA
  and exposure time are already known from the ephemeris. This applies to both NEOx (e93) and any PhotPipe
  re-reduction.
- [ ] **Fix 12 — field-star contamination flag.** For sidereal fields, measure the flux at the target's (trailed)
  aperture position on a frame where the target is elsewhere, and flag or reject frames above a threshold (0.02 mag
  here). SExtractor flags don't catch this (§6). DIA should remove it once the e93 photometry uses small, matched
  apertures (Fix 4).
- [ ] **Fix 13 — error bars.** Don't add a per-star-scatter zeropoint term to every point, as PhotPipe's `ZP_sig` does.
  Use the error on the mean zeropoint, and treat the zeropoint as a correlated (per-frame) term when fitting.
- [ ] **Fix 14 — observation planning.** At 0.505″/min, a 210 s exposure trails 1.77″ (≈ 1.2 × median FWHM). Keeping
  the trail ≲ 0.5 × FWHM needs exposures of ≲ 80 s here. Alternatively, rate-track the target, but then the *stars*
  trail and the zeropoint needs the matching correction instead.

### Aperture units and selection (§7)

- [ ] **Fix 16 — make the aperture unit explicit.**
  - In `single_frame_aperture_photometry` and `perform_aper_photometry`, accept an astropy `Quantity`, or separate
    `radius_arcsec` and `radius_pix` arguments.
  - In `pipeline_aper_photometry.py`, replace the bare positional `aperture_radius` with `--radius-arcsec`,
    `--radius-pix` or `--radius-fwhm`, defaulting to an FWHM multiple.
  - Write the unit into the ECSV column metadata, and the filename label, alongside the zeropoint aperture (Fix 4).
- [ ] **Fix 17 (minor):** fix the mixed-unit `CircularAnnulus((ra, dec), ...)` in the `background_subtract=True` branch
  of `single_frame_aperture_photometry`, or remove that branch.
- [ ] **Fix 18 — PhotPipe:**
  - Commit the local `LCOMUSCEP07` (and other MuSCAT) entries in `~/git/photometrypipeline/setup/telescopes.py`, so the
    circulated reduction is reproducible.
  - Report the `n_target`/`n_bkg` bug upstream.
  - For trailed targets, prefer `-fixed_aprad` (≳ 1.5–2 × worst FWHM + half the trail) or Fix 11 over the automatic
    curve-of-growth choice.

### Circulated results

- [ ] **Fix 15:** tell the recipients of the PhotPipe 2026-07-12 lightcurve:
  - The magnitudes are about **0.09 mag too faint** (trail loss) and carry a seeing-correlated systematic of order
    ±0.05 mag.
  - Frames 0091, 0092, 0099 and the other contaminated frames listed in §6 are affected by field stars.
  - Slow features at the start and end of the night coincide with the worst seeing.

  Re-issue after Fixes 11–13, or with a fitted seeing term and the contaminated frames removed (χ²_red ≈ 1.0).

---

## Verification performed

- **e93 zeropoint provenance (§3):** header and DB comparisons on all 86 ep07 frames.
- **NEOx aperture size:** photutils re-measurement against `FLUX_APER` on 15 frames (6.01 px each), plus the apophis2
  config diff.
- **PhotPipe settings:** read from its LOG (SExtractor command line, chosen aperture, catalog transformation, rejected
  frames). Transformation coefficients read from `~/git/photometrypipeline/catalog.py:1362` (`8514d04`). Catalog colours
  taken from frame 0058's `.ldac.db`.
- **Same pixels:** PhotPipe's e91 and NEOx's e92 data arrays are identical (frame 0058).
- **dZP decomposition:** per-frame star 5 px/6 px flux ratios on all 84 joined frames.
- **Lightcurve bias:** per-frame star 5″/6 px flux ratios on all 86 frames, combined with the e92 and e93 zeropoints.
- **Run provenance:** `PipelineProcess` 1599208–1599212 (inputs, logs, timings). `configs_dir` was this path on
  apophis2. The `sextractor_neox_ldac.conf` symlink in `/apophis/eng/rocks/Hera/20260712/` on this machine was created
  after the e92 catalogs, so it does **not** show the config used.
- **Committed `update_frame_zeropoint` call:** `inspect.signature(...).bind(...)` with `frame_filepath=` raises
  `TypeError`.
- **PhotPipe scatter (§6):**
  - The lightcurve comes from `photometry_65803_Didymos__1996_GT_.dat` (84 frames, excluding 0066/0067), fitted with a
    4th-order Fourier series at P = 2.2600 h plus a linear term.
  - `ZP_sig` definition read from `~/git/photometrypipeline/pp_calibrate.py:360`.
  - Tracking mode from the e92 headers (`SRCTYPE`, `RATRACK`, `DECTRACK`, `L1ELLIP`). Rate and PA from a linear fit to
    PhotPipe's `source_ra`/`source_dec`.
  - Trail loss and field-star contamination measured per frame on all 86 frames.
  - The simulated aperture loss and the SMTN-003 comparison use `aperture_trail_loss()`/`snr_trail_loss()` below, and
    a re-run of the SMTN-003 notebook's velocity/seeing grid (2 × 15 s snaps, 2 and 4 s gaps, double Gaussian).
  - The aperture-dependence test re-measured Didymos on e92 at 5/6/8/10/12 px, each calibrated with the e92 zeropoint
    plus the star-measured aperture correction. The 5 px values reproduce PhotPipe to a median of 0.000.
- **Aperture units and curve of growth (§7):**
  - History from `git log -L` on `single_frame_aperture_photometry` and `perform_aper_photometry`, plus
    `git log` on `pipeline_aper_photometry.py`.
  - The unit test used the median `aperture sum`, `aperture sum err` and `SNR` of the four
    `aper_p_Didymos*` tables (`_712_06_4`, `5snr_712_06_13`, `2_712_06_13`, `_712_06_13`; same 86 frames, same order).
    The `aperture sum err` ratios equal the radius ratios exactly, as they should.
  - PhotPipe's method read from `pp_photometry.py` and `_pp_conf.py` at `8514d04`. Its choice and rejected frames come
    from its LOG; the curve from `aperturephotometry_curveofgrowth.dat`.
  - `LCOMUSCEP07` absent from `git show HEAD:setup/telescopes.py`.
- **Not verified:**
  - The cause of the 0.058 vs 0.092 mag difference between PhotPipe's curve-of-growth gap and §6's synthetic trail
    loss (§7).
  - BANZAI's photometry aperture and reference catalog (§3); only their combined effect is measured.
  - Whether the seeing-correlated residual that the trail loss doesn't explain (§6 caveat) is instrumental or
    intrinsic. That needs other nights.

## Reproducing the checks

Run from `neoexchange/` with Django set up as in the notebook's first cell.

**Header provenance for one frame:**

```python
from astropy.io import fits
d = "/apophis/eng/rocks/Hera/20260712/coj2m002-ep07-20260712-0058-"
for s in ['e92.fits', 'e92.bkgsub.fits', 'e92.rms.fits', 'e93.fits']:
    h = fits.getheader(d + s)
    print(f"{s:16s} L1ZP={h.get('L1ZP')} L1ZPERR={h.get('L1ZPERR')} L1ZPSRC={h.get('L1ZPSRC')}")
```

**Star flux ratio between two apertures on one frame:** used for the NEOx aperture check, the dZP decomposition and
the lightcurve bias.

```python
from photutils.aperture import CircularAperture, aperture_photometry

def star_flux_ratio(frame_base, r_num, r_den):
    """Median ratio of star fluxes in apertures r_num/r_den (px) on <frame_base>.bkgsub.fits."""
    cat = fits.getdata(frame_base + "_ldac.fits", 2)
    img = fits.getdata(frame_base + ".bkgsub.fits").astype(float)
    c = cat[(cat['FLAGS'] == 0) & (cat['FLUX_APER'] > 2e3) & (cat['FLUX_MAX'] < 3e4) & (cat['CLASS_STAR'] > 0.8)]
    pos = np.vstack([c['XWIN_IMAGE'] - 1, c['YWIN_IMAGE'] - 1]).T
    num = aperture_photometry(img, CircularAperture(pos, r=r_num), method='exact')['aperture_sum']
    den = aperture_photometry(img, CircularAperture(pos, r=r_den), method='exact')['aperture_sum']
    return np.median(np.asarray(num) / np.asarray(den))

base = "/apophis/eng/rocks/Hera/20260712/coj2m002-ep07-20260712-0058-e92"
print(2.5 * np.log10(star_flux_ratio(base, 5.0, 6.0)))          # predicted PP - NEOx dZP (before the +0.005 PS1->SDSS term)
print(2.5 * np.log10(star_flux_ratio(base, 5.0 / 0.267, 6.0)))  # ZP correction from a 6 px to a 5" aperture
```

**dZP join:**

```python
qs = Frame.objects.filter(block_id=35906, frametype=Frame.NEOX_RED_FRAMETYPE, filter='rp') \
                  .values('filename', 'zeropoint', 'zeropoint_err', 'exptime', 'fwhm')
db_t = Table(rows=list(qs))
pp = Table.read(Phot_path, format='ascii')
pp.rename_column('file', 'filename')
m = join(pp, db_t, keys='filename')
m['dZP'] = m['ZP'] - 2.5 * np.log10(m['exptime']) - m['zeropoint']
```

**Trail loss and field-star contamination for one frame (§6):** `ra`, `dec` are the target position (e.g. PhotPipe
`source_ra`/`source_dec`); `rate_ra`, `rate_dec` are the sky motion in ″/s, with `rate_ra` already multiplied by
cos δ.

```python
from astropy.wcs import WCS

def trail_vector(frame_base, ra, dec, rate_ra, rate_dec):
    """Trail length (px) and unit direction in pixel coordinates for this frame's exposure."""
    h = fits.getheader(frame_base + ".fits")
    w, exp = WCS(h), h['EXPTIME']
    x0, y0 = w.all_world2pix([[ra, dec]], 0)[0]
    x1, y1 = w.all_world2pix([[ra + rate_ra * exp / 3600 / np.cos(np.radians(dec)),
                                dec + rate_dec * exp / 3600]], 0)[0]
    length = np.hypot(x1 - x0, y1 - y0)
    return length, np.array([x1 - x0, y1 - y0]) / length

def trail_loss(frame_base, length, u, r_ap=5.0, nstep=13):
    """Extra magnitude lost by a source trailed by <length> px (direction u) in an r_ap aperture, relative to a star."""
    cat = fits.getdata(frame_base + "_ldac.fits", 2)
    img = fits.getdata(frame_base + ".bkgsub.fits").astype(float)
    c = cat[(cat['FLAGS'] == 0) & (cat['FLUX_APER'] > 2e3) & (cat['FLUX_MAX'] < 3e4) & (cat['CLASS_STAR'] > 0.8)]
    pos = np.vstack([c['XWIN_IMAGE'] - 1, c['YWIN_IMAGE'] - 1]).T
    f0 = np.asarray(aperture_photometry(img, CircularAperture(pos, r_ap), method='exact')['aperture_sum'])
    steps = np.linspace(-length / 2, length / 2, nstep)
    ft = np.mean([np.asarray(aperture_photometry(img, CircularAperture(pos + s * u, r_ap), method='exact')['aperture_sum'])
                  for s in steps], axis=0)
    return -2.5 * np.log10(np.median(ft / f0))            # 0.067-0.112 mag for 6.6 px trail, 5 px aperture

def star_contamination(ref_base, ra, dec, length, u, target_counts, r_ap=5.0, nstep=13):
    """Magnitude by which field stars brighten the target, measured at the same sky position on a reference frame
    (sidereal tracking) where the target is elsewhere."""
    img = fits.getdata(ref_base + ".bkgsub.fits").astype(float)
    x, y = WCS(fits.getheader(ref_base + ".fits")).all_world2pix([[ra, dec]], 0)[0]
    pts = np.array([[x, y]]) + np.outer(np.linspace(-length / 2, length / 2, nstep), u)
    fc = np.mean(np.asarray(aperture_photometry(img, CircularAperture(pts, r_ap), method='exact')['aperture_sum']))
    return 2.5 * np.log10(1 + max(fc, 0) / target_counts)
```

**Simulated trail loss and SMTN-003 comparison (§6 cross-check):** no data needed. Rates in ″/min (1°/day = 2.5″/min).

```python
import numpy as np

def trail_image(fwhm, trail, kind='moffat', beta=2.5, half=8.0, step=0.02):
    """Unit-flux image (arcsec grid) of a PSF smeared along x by <trail> arcsec."""
    g = np.arange(-half, half + step / 2, step)
    X, Y = np.meshgrid(g, g)

    def psf(x0):
        r2 = (X - x0)**2 + Y**2
        if kind == 'moffat':
            alpha = fwhm / (2 * np.sqrt(2**(1 / beta) - 1))
            return (1 + r2 / alpha**2)**(-beta)
        s = fwhm / 2.3548                       # SMTN-003 double Gaussian
        return np.exp(-r2 / (2 * s * s)) / s**2 + 0.1 * np.exp(-r2 / (8 * s * s)) / (4 * s**2)

    centres = np.linspace(-trail / 2, trail / 2, max(2, int(40 * trail / fwhm) + 1))
    img = sum(psf(x0) for x0 in centres)
    return X, Y, img / img.sum()

def aperture_trail_loss(fwhm, rate_arcsec_min, texp, radius, **kw):
    """Extra loss (mag) of a trailed target relative to a star in a circular aperture of <radius> arcsec."""
    trail = rate_arcsec_min * texp / 60.0
    frac = []
    for t in (1e-6, trail):
        X, Y, img = trail_image(fwhm, t, **kw)
        frac.append(img[X**2 + Y**2 <= radius**2].sum())
    return 2.5 * np.log10(frac[0] / frac[1])

def snr_trail_loss(fwhm, rate_arcsec_min, texp, **kw):
    """Sky-limited S/N loss (mag) for optimal extraction: 1.25 log10(neff_trail / neff_star)."""
    trail = rate_arcsec_min * texp / 60.0
    half = 6 * fwhm + trail
    neff = [1 / np.sum(trail_image(fwhm, t, half=half, **kw)[2]**2) for t in (1e-6, trail)]
    return 1.25 * np.log10(neff[1] / neff[0])

# Didymos 2026-07-12: 0.505"/min (0.202 deg/day), 210 s; 5/8/12 px at 0.266"/px
for fw in (1.0, 1.44, 1.7):
    print(fw, [round(aperture_trail_loss(fw, 0.505, 210, r), 3) for r in (1.33, 2.13, 3.19)])
print(snr_trail_loss(1.44, 0.505, 210, kind='dgauss'), snr_trail_loss(1.44, 0.505, 210))  # 0.149, 0.118

def smtn003(rate_arcsec_min, fwhm, texp):
    """SMTN-003 S/N (trail) and detection losses, with the rate in "/min instead of deg/day."""
    x = rate_arcsec_min * texp / fwhm / 60.0
    return (1.25 * np.log10(1 + 0.761 * x**2 / (1 + 1.162 * x)),
            1.25 * np.log10(1 + 0.420 * x**2 / (1 + 0.003 * x)))
```
