# Didymos 2026-07-12 photometry notebook — summary

Source: `docs/Hera_2026/2026_07_12_photometry.ipynb`

## Context

- Target: (65803) Didymos
- Telescope/camera: COJ 2 m, `coj2m002-ep07`
- Night: 2026-07-12, Block **35906**, r′ filter, 210 s exposures
- ~86 frames, numbered 0058–0143
- `e92` = reduced frames; `e93` = difference-imaged (subtracted) frames

## What was investigated

### 1. Aperture size on the e93 (subtracted) frames — cells 2–14

Aperture photometry on the subtracted frames at radii 13, 8, 5 and 4 px. (The r = 13 light-curve plot is mislabelled "Aperture radius = 15".)

Using the table's `SNR` column:

| radius | mean SNR |
|--------|----------|
| 13 px  | 3.7      |
| 8 px   | 7.5      |
| 5 px   | 13.4     |
| 4 px   | ~15–21 per frame |

Sky / subtraction-residual noise dominates, so smaller apertures win. A second "rough" SNR estimate, `apsum / sqrt(apsum_err)`, gives 14 / 22 / 31 for r = 13 / 8 / 5 — that formula is not really an SNR, but the trend is the same.

### 2. Which e93 frames are bad, and why — cells 15–18, 34–39

At r = 13, **16 of 86** frames fail the cuts:

- 6 have a *negative* aperture sum → NaN mag: 0079, 0081, 0082, 0086, 0090, 0143 (0090 has an aperture sum of −92 900)
- 10 have magerr > 1: 0092, 0094, 0098, 0112, 0114, 0116, 0118, 0135, 0136, 0141

`examine_subtractions` (`core/views.py`) splits each e93 into a 3×3 grid and flags a frame if any box mean/median exceeds `badness_threshold`:

| `badness_threshold` | frames flagged | % |
|---------------------|----------------|---|
| 1000 (default)      | 2 (0086, 0090) | 2.3 |
| 400                 | 18             | 20.9 |

400 is a much better match to what the photometry cuts were saying. Frames flagged at 400: 0058, 0059, 0060, 0061, 0063, 0064, 0071, 0075, 0076, 0079, 0080, 0086, 0089, 0090, 0128, 0130, 0133, 0134.

The flagged frames show whole grid boxes with means of −500 to −2900 — large block-shaped negative residuals from bad subtraction. Notebook comment: *"super negative SNR when we get the weird block distortions — can use this to recognize them"*.

A `bad_sub_highlighter()` helper (defined in the notebook) reads the `examined_subtractions_table_2026-07-12.ecsv`, selects boxes with mean < −100 and std > 34.5, and draws red rectangles on those boxes over a grid of the flagged e93 frames.

### 3. PhotPipe photometry on the e92 (unsubtracted) frames — cells 21–33

From the DART-format file `lcogt_coj-PP_ep07_20260712_4253588_65803didymos_photometry.tab`:

- Instrumental mag errors all ≤ 0.035 mag
- SNR (= 1.0857 / inst_sig) ≈ 30–45
- ZPs stable at 24.79–24.83 ± 0.01
- **18 frames carry SExtractor flags**: 11 × flag 2 (deblended), 7 × flag 3 (neighbour-biased + deblended). Includes 0065, 0068, 0071, 0104, 0105, 0128, 0129, 0130, 0131, … — Didymos passing close to field stars.

### 4. SNR vs airmass — cells 24–29

Field altitude goes 65° → 81° (transit) → 48°; airmass 1.0–1.5. Two regions were boxed on the SNR–airmass plot:

- **"Bad Frames"**: a pair of low-SNR frames right at transit — 0069, 0070 (airmass ≈ 1.04, SNR ≈ 37)
- **"Time Dep. Poor SNR"**: steady SNR decline from frame 0128 onward as airmass climbs past ~1.2 (SNR 31–37)

Frames with SNR < 38 are essentially 0069/0070 plus everything from 0128 to the end of the block.

### 5. ZP cross-check — cell 31

Overlay of DB frame ZPs, exposure-time-corrected ZPs (+2.5 log10 210), e93 r = 5 aperture ZPs and PhotPipe ZPs on one plot, with SExtractor-flagged points marked.

## Take-aways for reducing light-curve scatter

1. The dominant driver of e93 light-curve scatter is **bad subtractions** (~20 % of frames), not photon noise. Catching them needs `badness_threshold ≈ 400`, not the default 1000 — and a *negative*-mean criterion may be more diagnostic than the current one.
2. Use a **4–5 px aperture** on the subtracted frames; 13 px is ~3.5× worse in SNR.
3. The last ~15 frames (≥ 0128) degrade with airmass, and ~18 frames have star-contamination flags in the e92 photometry. Both sets overlap with the e93 failures, so the same frames are hurting both reduction routes.
4. Intended follow-ups listed in cell 20 that were never done:
   - per-frame SNR and mag-scatter plots from NEOx aperture photometry
   - the same from PhotPipe aperture photometry
   - the same for DIA photometry
   - find frames with high scatter / large offsets

## Caveats / bugs noticed in the notebook

- Every data path is under `/home/mwalker/…` (`Didymos_data`, `didymos_photometry`); none of it exists on the current machine, so the notebook cannot be re-run without copying the data over.
- Cell 23: "max error frame = 0058" is spurious — `argmax()` is called on a scalar, so it always returns index 0.
- Cell 16: `if fname:` should be `if frame:` (the NOT FOUND branch can never trigger).
- Airmass (cells 24–25) is computed from `StaticSource` positions rather than Didymos itself — fine as a proxy, but the loop appends every StaticSource per frame, so it only lines up with the frame list if there is exactly one StaticSource per block.
- Cell 27 x-axis label says "Airmass (degrees)".
- `examine_subtractions` docstring says boxes *above* the threshold are bad, but all the flagged boxes here are strongly *negative*; worth checking what `determine_bad_subtractions_in_box_stats` actually compares (probably `abs()`).

## Key files referenced

| Purpose | Path |
|---------|------|
| e93 aperture phot, r = 13 | `didymos_photometry/aper_p_Didymos_712_06_13.ecsv` |
| e93 aperture phot, r = 8  | `didymos_photometry/aper_p_Didymos2_712_06_13.ecsv` |
| e93 aperture phot, r = 5  | `didymos_photometry/aper_p_Didymos5_712_06_13.ecsv`, `aper_p_Didymos5snr_712_06_13.ecsv` |
| e93 aperture phot, r = 4  | `didymos_photometry/aper_p_Didymos_712_06_4.ecsv` |
| e93 frames | `Didymos_data/f06_012_e93/` |
| PhotPipe (DART) e92 photometry | `Didymos_data/subtraction_analysis/lcogt_coj-PP_ep07_20260712_4253588_65803didymos_photometry.tab` |
| Subtraction-quality table | `Didymos_data/subtraction_analysis/examined_subtractions_table_2026-07-12.ecsv` |
| Light-curve plots written | `Didymos_data/tmp_7_12_LC_{2,8,5,5s,4s}` |
