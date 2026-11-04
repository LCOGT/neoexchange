# HOTPANTS difference imaging: the failing tile and how we call HOTPANTS

Investigation of 2026-11-04 (Fix 23 in `2026_07_12_zeropoint_analysis.md`). Data: Hera Block 35906, 2026-07-12,
`coj2m002-ep07` (MuSCAT4 r′), 86 × 210 s frames, reference `reference_coj_ep07_rp.fits` (10 × 60 s from 2026-07-10).
Files under `/apophis/eng/rocks/Hera/20260712/`.

## Summary

- One of the nine HOTPANTS regions, **region 05 = `[1365:2048, 683:1365]`** (the mid-right tile), has a collapsed
  kernel fit in **68 of 86** frames: kernel sum 0.6–2.1 against 2.8–2.9 in the other eight regions, final stamp
  sigma 3–134 against ≈1.0. Only the worst ~18 frames show up at `examine_subtractions`' 400-count threshold; the
  rest are quietly wrong too. The region holds the brightest star in the field (≈1780, 880 px, saturated with a
  bleed column).
- **Cause: we pass HOTPANTS no mask images.** BANZAI's BPM does flag the saturated pixels, but the e92 we subtract
  is SCI-only, SExtractor's `.bkgsub` check image carries no mask, and `run_hotpants` passes neither `-imi` nor
  `-tmi`. HOTPANTS's fallback `-iu SATURATE` threshold runs on the background-subtracted image (where SExtractor's
  inflated background under the star drops ~40 % of the plateau below threshold) and, more importantly, its
  substamp search only looks for bad pixels *inside its own stamp cell*: a saturated star 4 px outside a cell seeds
  a "substamp" on its 36 000-count wings, and that one substamp wrecks the region's fit.
- **Fix (code, 2026-11-04):** `create_hotpants_mask()` (`photometrics/image_subs.py`) masks `e92 ≥ SATURATE` plus
  any BPM pixels, grown by the substamp half-width (`-rss`, ≈32 px), and `determine_hotpants_options()` passes it
  as `-imi`. Region 05 is repaired on every frame tested; the other regions are unchanged to <0.01 mag at Didymos.
- **ZUDS:** no upstream changes since the commit the local checkout is on (16a8f03, 2020-08-06). Our call is a
  faithful copy of `zuds/hotpants.py` except for the parts that needed ZUDS's own infrastructure (the mask, the
  weight-map noise images) and two option choices (`-ko 4 -bgo 0`); the missing mask is the one that matters.

## 1. Symptom

`examine_subtractions` (`core/views.py`) splits each e93 into a 3 × 3 grid and takes the mean/std of a 21 × 21 px box
at each tile centre. On the 86 r′ frames (table `subtraction_analysis/examined_subtractions_table_2026-07-12.ecsv`):

| tile | median box mean | min | frames with \|mean\| > 400 |
|---|---|---|---|
| mid-right (HOTPANTS region 05) | **−96.6** | −555.8 | **17** |
| mid-left / mid-mid / low-mid | −2.3 / 1.9 / −0.2 | −1014 / −2880 / −2259 | 1 each (0090, 0090, 0086) |
| the other five | ≈0 | > −8 | 0 |

The e93 headers carry HOTPANTS's own per-region diagnostics (`-hki`): `KSUMnn` (kernel sum = image/template flux
ratio), `FSIGnn` (final stamp figure of merit), `X2NRMnn` (mean (diff/noise)²). Census over all 86 production e93s,
flagging a region when `FSIG > 3` or its `KSUM` differs from the frame's median by > 0.3:

- region 05 bad in **68 / 86** frames (`KSUM05` 0.60–2.14, `FSIG05` 3.2–134); median `FSIG05` 12.5 against 1.05–1.11
  elsewhere;
- region 01 bad in 0086 (`KSUM` 0.25, `FSIG` 300), regions 03/04/05 bad in 0090 (the frame with the cloud/gradient,
  `L1SIGMA` 97) — 0086, 0089, 0090 are the three sharpest frames (FWHM 1.31–1.36″ vs template 1.44″);
- `KSUM` ≈ 2.8–2.9 is *expected*: the template is ten 60 s frames scaled to ZP 25 (`normalize()`), i.e. a 60 s
  equivalent image, against 210 s science frames: 210/60 ÷ 10^(0.4 (25 − 24.8)) = 2.9. Not a bug.

Didymos sat in region 04 (the centre tile; x 699–1328, y 1071–1137) all night, so region 05's failure mostly
contaminates the tile statistics and the background of the centre-right border, not the target aperture directly;
the frames that do hurt the lightcurve are the ones where the centre region failed too (0090; 0086's region 01).

## 2. Mechanism

Re-running the production command line on frame 0063 with `-v 2` (production discards HOTPANTS's output) and
reading `hotpants` 5.1.11 (`~/git/zuds-pipeline/hotpants/`, the fork ZUDS vendors) gives the chain:

1. **The flags exist but never reach HOTPANTS.** The archive e91 BPM has bit 2 on 3815 pixels, exactly the
   `e92 ≥ SATURATE` set (3803). `run_pipeline` writes the e92 as a single SCI HDU, SExtractor's `-BACKGROUND`
   check image (`-inim`) has no mask, and `determine_hotpants_options()` (`photometrics/external_codes.py`) builds
   the command without `-imi`/`-tmi`. The BPM is only ever used for the reference *weight* map
   (`create_weight_image`).
2. **`-iu SATURATE` under-flags.** It is applied to the `.bkgsub` image. SExtractor's BACK_SIZE 64 background mesh
   balloons under the bright star (1393 counts vs 858 sky), so ≈40 % of the 119–122 k plateau falls below 117 760
   after subtraction: 2225 of 3803 saturated pixels are flagged.
3. **Flagged pixels do not protect stamp selection.** In `functions.c` `getPsfCenters()` / `checkPsfCenter()` scan
   for the brightest peak in each 85 × 85 px stamp cell and reject a candidate only if a bad pixel (`bbit = 0xbf`)
   lies in the part of its 65 × 65 substamp box *inside the cell* (`if (k >= xLen) continue`). `makeInputMask()`
   grows the bad pixels by the kernel half-width, but `spreadMask()` writes only `FLAG_OK_CONV` (0x40), the one bit
   `bbit` excludes, so the spread never affects stamp selection. On 0063 the star core is at (1781, 924); the stamp
   cell `xs=405, ys=297` (region coords) ends at x = 1769; its brightest pixel is the star's spike ramp at
   (1769, 895) — 36 000 counts, the top-ranked substamp of the region — and the fit on that truncated star gives
   `KSUM05 = 1.25`, `FSIG05 = 90`.

So an *external* mask has to carry the geometry HOTPANTS does not: every pixel within a substamp half-width of
saturation must be ineligible as a substamp centre. Growing the saturation mask by 3 px happened to work on 0063
(one masked pixel crossed the cell edge) but fails on 0090/0120/0130 at half the substamp width; the full `-rss`
growth works on all.

## 3. Experiments (frame 0063 unless stated; re-runs into scratch, inputs read-only)

Scored by per-region `KSUM`/`FSIG`, the 3 × 3 tile means, and a 6 px aperture at Didymos' catalogued position.

| variant | region 05 (`KSUM`, `FSIG`, tile mean) | other frames / notes |
|---|---|---|
| A production command line | 1.25, 90.1, −411 | reproduces the e93 on disk exactly |
| B1 `-imi` science mask (≥ 0.9 SATURATE on `.bkgsub`, grown 3 px) | 2.86, 1.08, −6 | 0086 region 01 and 0090 regions 04/05 still bad |
| B6 same mask, no growth; B7 `-iu 0.9·SATURATE` | 1.25, 90 | growth is what matters, not the threshold |
| P1 `-imi` = (`e92 ≥ SATURATE` ∪ `.bkgsub ≥ 0.9 SATURATE`) grown by `rss` (32 px) | 2.87, 1.07, −5 | fixes region 05 on 0063/0086/0090/0120/0130; half-`rss` growth fails 0090/0120/0130 |
| B2–B5 template masks (zero coverage, zero pixels, bright cores, bad rms) | 1.25, 90 | no effect |
| C/M fixed noise maps (finite `BIG_RMS` instead of ∞ → resampled garbage; masked saturation) | as B | no measurable effect |
| G `-ft 10` (substamp peak threshold 10σ instead of 20σ) | — | also repairs 0086 region 01 and 0090 regions 03/04; ≤ 0.01 mag at Didymos on good frames |
| D `-bgo 0` (constant background, both inputs are background-subtracted) | — | also repairs 0090 region 04 (and 0086 region 01 with P1) |
| E `-ko 4 -bgo 0` (ZUDS's choice) | all nine regions destroyed | ≈12 substamps per region cannot support a 4th-order spatial kernel |
| K `-c i` (convolve the image) | — | halves the e93 noise (MAD 22 vs 35) but convolves Didymos: +0.02 … +0.17 mag in a 6 px aperture → not usable with small apertures |
| J `-nsx/-nsy 10` | — | same as G |

Substamp starvation is general: with the default `-ft 20` (peak ≥ 20 σ of the *template* sky noise, i.e. roughly
r′ ≲ 14.6 here) the 2048² frame yields ≈110 substamps, 20 of 36 stamp cells in region 05 find none, and the kernel
(3 Gaussians × orders 6/4/2 = 49 basis functions × `-ko 2` = 294 unknowns per region) is fitted from ~12 stars.

## 4. Night-wide impact on Didymos (all 86 r′ frames)

All 86 r′ frames re-subtracted in scratch with the production command line plus (P1) the `rss`-grown science mask
and (P2) the mask plus `-ft 10`; same noise images as production. Didymos measured with a 6 px aperture and a
15–25 px sky annulus at the positions in `aper_photometry_35906_rL1ZPAPER.ecsv`; p2p = 1.4826·MAD of consecutive
differences / √2, as in Fix 22.

| | production | P1 mask | P2 mask + `-ft 10` |
|---|---|---|---|
| frames with a failed region | 68 (region 05 in 67) | **2** (0086 region 01, 0090 region 04 — the two sharpest frames) | 3 (region 05 on 0105/0106/0108, FWHM 1.10″, `KSUM` 2.0–2.5 but `FSIG` ≈1.3) |
| median `FSIG05` | 12.5 | 1.13 | 1.10 |
| Didymos: p2p scatter | 0.0377 | 0.0377 | 0.0367 |
| Didymos: MAD about a 7-point running median | 0.050 | 0.050 | 0.056 |
| frames changed by > 0.02 mag | — | **0 of 86** (identical) | 6 (0065/0066/0069/0127 ±0.02–0.03, 0090 +0.10, 0129 −0.08) |

HOTPANTS fits each region independently and Didymos never left region 04, so the mask repairs the mid-right tile
without touching a single Didymos measurement: the r′ curve's scatter is set by photon/sky noise and the
unflagged-region residuals, not by the failed tile. `-ft 10` does perturb the centre-region kernel (six frames move,
two by ≈0.1 mag, and the running-median scatter gets slightly worse) for no net gain, so it is not adopted. The two
remaining failures are the sharp frames where the template (median FWHM 1.44″) is being *sharpened* (`-c t` forced);
0090 is the cloud-affected frame already excluded from the lightcurve.

## 5. ZUDS and HOTPANTS upstream

- `zuds-survey/zuds-pipeline`: last commit `16a8f03` (2020-08-06) = the local `~/git/zuds-pipeline` checkout
  (local diff is two debug prints). No updates.
- `zuds-survey/hotpants`: fork of `acbecker/hotpants` 5.1.11; adds only a macOS `Makefile` check (`1d7065f`,
  2018). `acbecker/hotpants` master (2017) adds two compile fixes in `extractkern.c` over LCO's `6d85a93` SRPM
  (2013); nothing that changes results. Both the workstation and apophis2 binaries report 5.1.11.
- What `zuds/hotpants.py` does that `determine_hotpants_options()` does not:

| ZUDS | NEOexchange | effect here |
|---|---|---|
| `-imi submask` = science mask ∪ aligned reference mask (incl. SWarp zero-weight) | nothing | **the failure** |
| noise = 1/√weight with `BIG_RMS` at masked and ≥ 0.9·SATURATE pixels | science: SExtractor `BACKGROUND_RMS`; template: 1/√weight incl. ∞, then LANCZOS3-resampled (375 k zeros, 4.5 k negatives) | not measurable on the fits; worth cleaning up |
| `-ko 4 -bgo 0` | defaults `-ko 2 -bgo 1` | `-ko 4` catastrophic here; `-bgo 0` mildly helpful |
| `+150` count pedestal on the bkgsub image | none | none |
| `satlev = 5e3` (ZTF units) | `MAXLIN`/`SATURATE` from the header, for both `-tu` and `-iu` | template `-tu` is in the wrong units (template ≈ sci/2.9) but changing it does nothing |

Also noticed, not acted on: the aligned template has a 64-row / ~10-column zero strip (pointing offset between the
07-10 reference and 07-12 science frames) that HOTPANTS treats as valid data, so the e93 shows the raw science image
there and `X2NRM` is huge in regions 00/01/06; harmless for a centre-field target.

## 6. What changed and what is left

**Done (Fix 23):** `create_hotpants_mask(fits_file, dest_dir, halfwidth)` in `photometrics/image_subs.py`;
`determine_hotpants_options()` calls it with the `-rss` value and adds `-imi <e92>.mask.fits`. Tests:
`TestCreateHotpantsMask` (`test_image_subs.py`), updated `TestDetermineHotpantsOptions`/`TestHotpantsRunner`
expectations (self-subtraction regression pixels moved by < 4 counts).

**Candidates, not adopted without a decision:**
- `-ft 10` (or `-nsx/-nsy 10`): more substamps; repaired 0086/0090 in the five-frame tests but over the whole
  night it moves six Didymos points (two by ≈0.1 mag), leaves region 05 marginal on the three sharpest frames and
  does not reduce the scatter (§4). Not recommended as is.
- `-bgo 0`: both inputs are background-subtracted; a constant per region is the physically right model. Repaired
  0090's centre region in the five-frame test; not run night-wide.
- Let HOTPANTS choose the convolution direction (drop `-c t`), or convolve the image only when the science FWHM is
  below the template's: the two residual failures (0086, 0090) and the three `-ft 10` marginals are all frames
  sharper than the 1.44″ template. Needs the photometry side to understand a convolved target (§3, variant K).
- Finite noise maps: write `BIG_RMS` instead of ∞ in `create_rms_image` before SWarp resamples the template rms;
  add `BIG_RMS` at saturation in the science rms.
- Mask the template's zero-coverage strip (`-tmi` from the aligned weight map) and make
  `examine_subtractions`' default threshold ≈400 with a signed (negative-mean) criterion.
- Re-running the DIA on 35906/36005 would change the e93 tiles and the `examine_subtractions` flags but not one
  Didymos measurement (§4), so the Fix 9/Fix 22 photometry stands; regenerate only if the e93 files themselves are
  a deliverable.
