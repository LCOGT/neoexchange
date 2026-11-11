# Accurate asteroid astrometry: reference epoch, proper motions, and what SCAMP, Rubin and Buie do

Written 2026-11-06 after the Didymos (65803) 2026-07-12 FTS/MuSCAT4 analysis (Block 35906). Companion to
`docs/Hera_2026/hotpants_dia_investigation.md`.

## 1. Summary

- NEOexchange's e92 WCS solutions are tied to Gaia star positions at **epoch 2000.0**, not at the date of
  observation. `get_vizier_catalog_table()` asks VizieR for the `RAJ2000`/`DEJ2000` columns of Gaia DR2/DR3, which
  VizieR computes by running the Gaia proper motions back from the catalogue epoch (2016.0 for DR3) to 2000.0.
  Nothing downstream moves the stars forward again. The WCS therefore describes the sky as it was 26 years before
  the exposure.
- The error is the mean proper motion of the reference stars times (t_obs − 2000.0). For the Didymos field it is
  0.17″ (+120 mas in RA·cosδ, +125 mas in Dec). It is field dependent, coherent across a night and across every
  frame reduced this way, and it goes straight into any astrometry measured from e92 frames and into the aperture
  placement of `perform_aper_photometry`, which does not centroid.
- The MPC/JPL catalogue debiasing does not remove it: those corrections fix the catalogue's errors relative to
  Gaia, so an observation reported with a Gaia catalogue code gets no correction.
- No SCAMP version propagates a local (`ASTREF_CATALOG FILE`) reference catalogue to the exposure epoch, including
  the 2.15.0 on the workstation and the 2.0.4 that produced the July data. The positions must be propagated by us
  before the file is written. Doing that brings the WCS to within 1 mas of Gaia at the epoch of observation and
  cuts SCAMP's reference residual from 0.13″ to 0.03″ (section 5.3).
- Rubin and Buie both propagate reference positions to the exposure epoch (sections 6 and 7); neither applies
  reference-star parallax; both measure mid-exposure time as start + exposure/2.
- PhotometryPipeline (section 8), which also fits with SCAMP against a local Gaia file, takes the catalogue-epoch
  columns (2016.0) and downloads the proper motions but never applies them: the same class of error at 40% of the
  size (≈ 45 mas on this field in 2026, which is what the 2016.0 variant of the SCAMP test gave).
- The rest of the error budget on this night (distortion, chromatic refraction, timing) is at the 20 mas level
  (section 9). Fixing the epoch is the whole story at the 0.1″ level.

Terminology used below: *frame* (ICRS, equinox J2000) is the orientation of the axes; *epoch* is the date the
star positions refer to. "J2000" in a VizieR column name means epoch 2000.0 as well as equinox J2000, which is the
trap this note is about.

## 2. What was found on 2026-07-12

The Didymos aperture photometry places its 6 px aperture at the HORIZONS ephemeris position mapped through the e92
WCS. The stacked target centroid sat a steady (−0.35, +0.45) px from that position in all four cameras all night
(0.268″/px). Because the offset is the same in g′ and z_s and has a component perpendicular to the motion, neither
chromatic refraction nor timing can produce it. The investigation (scripts and outputs under
`/data/tlister/hotpants_demo/dia_crosscheck/`) found:

| Check | Result |
|---|---|
| Cached reference file `GAIA-DR3_240.24-22.24_13.6484mx13.6484m.cat` vs Gaia DR3 `RAJ2000/DEJ2000` | identical to 0.000 mas for all 1013 stars |
| Same file vs Gaia DR3 `RA_ICRS/DE_ICRS` (epoch 2016.0) | median 112 mas apart |
| `OBSDATE` column written by `write_ldac` | 2015.5 for every star (wrong for both epochs) |
| Mean proper motion of the 1013 reference stars | (−4.27, −4.50) mas/yr → (−113, −119) mas over 26.5 yr |
| e92 WCS minus Gaia DR3 propagated to 2026.53, stars with S/N > 30, every 12th frame | g′ +120/+130, r′ +125/+120, i′ +126/+124, z_s +116/+122 mas (RA·cosδ / Dec); no trend with airmass 1.02–1.42 |
| Predicted target centroid − ephemeris position from that offset | (−0.44…−0.47, +0.45…+0.49) px |
| Measured stacked target centroid − ephemeris position | g′ (−0.34, +0.43), r′ (−0.37, +0.49), i′ (−0.42, +0.46), z_s (−0.37, +0.49) px, ±0.02–0.05 |
| Residual after also modelling the linear-WCS distortion along the track (cubic fit to star residuals) | mean of 4 bands (+0.07, −0.02) px = (19, −5) mas |
| HORIZONS 3σ orbit uncertainty on the night | 0.001″ |
| `Frame.midpoint` vs `DATE-OBS + EXPTIME/2`, e91 vs e92, 344 frames | identical |

The +19 mas along-track residual corresponds to 2 s of Didymos's motion and is at the level of the centroiding
systematics (moment centroid of a trailed source on a difference image versus windowed star centroids). A TT/UTC
confusion would have been 69 s = 2.2 px along the track and is excluded.

## 3. Frames, epochs and what the MPC expects

- Positions are reported in the ICRS (equinox J2000) **at the epoch of observation**. "Don't correct for parallax
  or UTC→TT" in the MPC guide (https://docs.minorplanetcenter.net/mpc-ops-docs/astrometry/getting-started/) refers
  to the asteroid: report topocentric positions at UTC times; the orbit fitter handles the rest.
- The reference stars must be where they are on the night: catalogue position + proper motion × (t_obs − t_cat).
  With Gaia the catalogue epoch is 2015.0 (DR1), 2015.5 (DR2) or 2016.0 (EDR3/DR3). Reference-star parallax is
  below 1 mas for a typical field and is not applied by anyone surveyed here.
- The astrometric catalogue is recorded with each observation (MPC 80-column catalogue code, ADES `astCat`;
  `astrometrics.sources_subs.translate_catalog_code` maps `GAIA-DR3` → `W` / `Gaia3`). The MPC and JPL use it to
  apply the catalogue debiasing tables (Chesley, Baer & Monet 2010, Icarus 210, 158; Farnocchia et al. 2015,
  Icarus 245, 94; Eggl et al. 2020, Icarus 339, 113596). Those tables correct each catalogue's zonal position and
  proper-motion errors relative to Gaia; the correction for a Gaia-reduced observation is zero. They cannot know
  whether the reducer applied the proper motions, so an epoch-2000 reduction reported as Gaia keeps its full offset.
  (Paper details cited from memory; check before quoting.)

## 4. What NEOexchange does today

Code path (`photometrics/catalog_subs.py`, `photometrics/external_codes.py`, `pipelines/processdata.py`):

1. `get_reference_catalog()` → `get_vizier_catalog_table()` queries VizieR `I/355/gaiadr3` (or `I/345/gaia2`) with
   `columns=['RAJ2000', 'DEJ2000', 'e_RAJ2000', 'e_DEJ2000', 'Gmag', 'e_Gmag', 'Dup']`, `Plx > 0`, `Gmag ≤ 18`
   (lines ~125–128 and ~195–197). The comment at line 127 already notes that `RA_ICRS/DE_ICRS` would be closer to now.
2. `write_ldac()` writes `XWIN_WORLD, YWIN_WORLD, ERRAWIN_WORLD, ERRBWIN_WORLD, MAG, MAGERR` and a constant
   `OBSDATE = 2015.5`. The file is cached per directory as `GAIA-DR3_<ra><dec>_<w>x<h>.cat` and reused by every
   frame of a night (and by later reruns in the same directory, e.g. `--tempdir /apophis/eng/rocks/Hera/<date>`).
3. `run_scamp()` runs `scamp <e91_ldac> -c scamp_neox_gaiadr3.cfg -ASTREF_CATALOG FILE -ASTREFCAT_NAME <cat>`
   (`-POSANGLE_MAXERR 1 -MATCH_FLIPPED N` for 2m0, `-DISTORT_DEGREES 3 -PROJECTION_TYPE TPV` for 1m0 Sinistro/FLI,
   otherwise `DISTORT_DEGREES 1`). The config has `ASTREFOBSDATE_KEY OBSDATE`, `STABILITY_TYPE INSTRUMENT`,
   `COMPUTE_PROPERMOTIONS Y`, `CORRECT_COLOURSHIFTS N`, `SN_THRESHOLDS 3,50`, `CROSSID_RADIUS 2`.
4. `updateFITSWCS()` copies the `.head` solution into the e92 and records `WCSSOLVR`, `WCSRFCAT`, `WCSNREF`,
   `WCSMATCH`, `WCSRDRES` (SCAMP's `ASTRRMS1/2` in arcsec) and `WCSDELRA/DE`.

SCAMP versions: the July 2026 e92 headers say `SCAMP-2.0.4` (2016 build on apophis2 / the production container);
the workstation has 2.15.0 (`scamp-2.15.0-1.el9`). The Docker image installs `scamp` from the LCO yum repo
(`Dockerfile` line 164), so the container version follows that repo.

A diagnostic that was visible all along: `WCSRDRES = '0.17449/0.15219'` on the July frames. A healthy fit of a
2m0 frame to Gaia gives about 0.03″ (section 5.3). Unapplied proper motions add 26 years of individual star motion
(tens of mas each) to the residual, on top of the mean offset absorbed by the linear terms.

### 4.1 Status: implemented 2026-11-10 (branch `fix/refcat-epoch-propagation`)

- `get_vizier_catalog_table` queries `RA_ICRS, DE_ICRS, e_RA_ICRS, e_DE_ICRS, pmRA, pmDE, e_pmRA, e_pmDE`
  (plus the `RAJ2000/DEJ2000` columns that `cross_match` still uses) for GAIA-DR2/-EDR3/-DR3 (`I/350/gaiaedr3`
  added); `propagate_gaia_positions()` moves the stars linearly from the catalogue epoch
  (`GAIA_CATALOG_EPOCHS`: 2015.5 / 2016.0) to the exposure mid-time and inflates the errors by μ_err·Δt.
- The epoch is a **TT Julian epoch** (`astrometrics.time_subs.datetime_to_jyear_tt`, pyslalib `sla_dtt`); see 5.6.
- `get_reference_catalog(..., epoch=header['obs_midpoint'])` is required for the Gaia catalogues and writes
  `<cat>_<ra><dec>_<w>x<h>_<epoch:.4f>.cat`, e.g. `GAIA-DR3_240.24-22.24_13.7093mx13.7093m_2026.5267.cat`;
  `OBSDATE` = that epoch. A cached file is reused only if it covers the field **and** is within
  `REFCAT_EPOCH_TOLERANCE` = 0.01 yr (3.65 d); files without an epoch suffix (everything written before this
  change, e.g. the per-night directories on apophis2) are never reused and are left in place.
- `COMPUTE_PROPERMOTIONS N` in both SCAMP configs.
- `updateFITSWCS` writes `WCSREPOC` (Julian yr, TT) from the catalogue filename reported in SCAMP's XML;
  `get_catalog_header` exposes it as `astrometric_epoch`; new nullable `Frame.astrometric_epoch`
  (migration `0075`) is filled by `make_new_catalog_entry`, `update_frame_zeropoint` and `create_frame`.
  Null = fitted before this change (Gaia positions at 2000.0 for every NEOX_RED frame reduced until now).
- `ScampProcessPipeline.check_fit_rms` warns in the pipeline log when a good fit has `WCSRDRES` > 0.1″.
- End-to-end on `coj2m002-ep07-20260712-0063` (SCAMP 2.15.0, workstation): LDAC positions agree with the
  independent `gaiadr3_field.fits` propagation to < 0.0001 mas; `WCSRDRES 0.0333/0.0338`; WCS − Gaia@2026.53 =
  **−0.1 ± 1.9 / +1.5 ± 2.0 mas** (371 stars) versus +130.5 / +125.6 mas for the production e92 of the same
  frame; a call with a mid-time 2 h later returns the cached file.

## 5. SCAMP

Source read at github.com/astromatic/scamp, master `72b7e76` (2026-06-11, 2.15.1dev); 2.0.4 is commit `fb3a9a9`
(2014-07-09). Full evidence in the research report; the key points:

### 5.1 Capabilities by version

| Version | Reference-catalogue epoch / proper-motion behaviour |
|---|---|
| 1.19 (2012) | `ASTREFOBSDATE_KEY` added: per-star `OBSDATE` is read into `sample->epoch`. |
| **2.0.4** (2014) | No Gaia, no VizieR (CDSclient catalogues only). No `ASTREFPROP*` keys, no proper-motion storage, no propagation. `OBSDATE` feeds only the (optional) per-source PM fit and output-catalogue epoch columns. |
| 2.4.3 (2016) | VizieR queries; GAIA-DR1 as a built-in catalogue. |
| 2.7.0 (2018) | GAIA-DR2 "without taking into account proper motions yet" (commit `f4bb412`). |
| 2.9.0 (2020) | `ASTREFPROP_KEYS` / `ASTREFPROPERR_KEYS` added ("Prepared support for proper motions", `982c783`): PM columns of a FILE catalogue are read into `sample->wcsprop` but never used by matching or solving. |
| 2.10.0 (2020) | GAIA-EDR3 "still without proper motions". |
| 2.12.0 (2023) | GAIA-DR3 built-in (`I/355/gaiadr3`, columns `RA_ICRS, DE_ICRS, …, pmRA, pmDE, …`). |
| **2.13.0** (2023-12, `46ac46a`) | `ASTREFEPOCH_TYPE ORIGINAL|MANUAL|FIELDS_AVERAGE`, `ASTREF_EPOCH`, `ASTREFREGUL_TYPE NONE|TIKHONOV`. Linear propagation `α += μα* Δt / cos δ`, `δ += μδ Δt`, error inflated by `μ_err Δt`, or by 10 mas/yr × Δt for stars without PM. **Applies only in the VizieR download branch** (`src/astrefcat.c` ~921–943); the FILE branch returns before it (~320–346) and `ASTREFEPOCH_TYPE` has no effect on FILE catalogues. Default `ORIGINAL`, so even `-ASTREF_CATALOG GAIA-DR3` uses 2016.0 positions unless asked. |
| 2.13.1 tag (2025-01) – 2.15.0 | As 2.13.0 plus bug fixes (`e8f21b4`, 2024-03: Dec error had overwritten the RA error). A "2.13.1" binary built between 2023-12 and 2024-03 carries that typo. |

The target epoch, when propagation is on, is a single run-wide value (`get_fields_meanepoch`, unweighted mean of
the input fields' mid-times, or `ASTREF_EPOCH`), fine for one exposure per run. The field epoch comes from
`MJD-OBS`, else `MJDSTART`, else `DATE-OBS`, plus `EXPTIME/2` (`src/fitswcs.c`, `src/samples.c`).

Other keywords, for the record: `COMPUTE_PROPERMOTIONS` fits a PM per cross-matched source from its multi-epoch
detections and writes it to the merged catalogue; it never alters the `.head`. With one exposure per run it is
meaningless, and if `OBSDATE` equals the exposure epoch every baseline is zero. Set it to `N`.
`CORRECT_COLOURSHIFTS` is a DCR colour term between instruments for that PM fit; `INCLUDE_ASTREFCATALOG` and
`ASTREF_WEIGHT` only weight the reference points. Nothing SCAMP writes (`.head`, XML) records the reference epoch
or whether propagation happened; the XML has a hard-coded `COOSYS epoch="2000.0"`. The official documentation does
not describe any of the `ASTREF*` keywords; they appear only in `scamp -dd`.

The Euclid ERO pipeline paper (Cuillandre, Bertin et al. 2024, arXiv:2405.13496, §5.2) states the same limitation
("inability to directly incorporate proper motions within the calibration process"), corrects Gaia DR3 to the
observation epoch itself and assigns a 10 mas/yr uncertainty to stars without proper motions.

### 5.2 Recipe for NEOexchange (all SCAMP versions)

Propagate before writing the FILE catalogue:

- Query `RA_ICRS, DE_ICRS, e_RA_ICRS, e_DE_ICRS, pmRA, pmDE, e_pmRA, e_pmDE` (plus `Gmag, e_Gmag, Dup, Plx` as now).
- `Δt = t_mid(Julian years) − 2016.0` (DR3/EDR3; 2015.5 for DR2).
- `XWIN_WORLD = RA_ICRS + pmRA·Δt / cos(DE_ICRS) / 3.6e6`, `YWIN_WORLD = DE_ICRS + pmDE·Δt / 3.6e6` (degrees;
  VizieR's `pmRA` is already μα·cosδ).
- Position errors `sqrt(e_pos² + (e_pm·Δt)²)`; stars without PM either dropped or kept unmoved with
  `+ (10 mas/yr · Δt)²`.
- `OBSDATE` = the epoch the positions are now at (the exposure mid-time), for honesty; it does not affect the fit.
- `COMPUTE_PROPERMOTIONS N` in the config.
- Record the epoch in the e92 header (e.g. `WCSREPOC` or similar) so a frame can be audited later; SCAMP won't.

The cache then becomes per-epoch: a night's frames span < 0.001 yr (a few mas), so one file per night directory is
fine, but a file must not be reused across nights without re-propagating. The cheapest robust rule is to key the
cache name on the epoch to 0.01 yr or to store the unpropagated columns and propagate at `run_scamp` time.

### 5.3 Test on r′ frame coj2m002-ep07-20260712-0063 (SCAMP 2.15.0, scratch only)

Same SExtractor catalogue, same config, four reference files; WCS evaluated against Gaia DR3 propagated to
2026.53 using 371 stars with S/N > 30:

| Reference file | WCS − Gaia@2026.53 (mas) | SCAMP `ASTRRMS1/2` (mas) |
|---|---|---|
| Production file (VizieR `RAJ2000/DEJ2000`, epoch 2000.0) | +96 ± 2, +115 ± 2 | 131 / 126 |
| Production run with 2.0.4 on apophis2 (from the e92 header) | +125, +120 | 174 / 152 (`WCSRDRES`) |
| Positions propagated by us to 2026.53, `OBSDATE` 2026.53 | **−0.4 ± 1.9, +1.2 ± 2.0** | **33 / 34** |
| Gaia 2016.0 positions + `PMALPHA_J2000`/`PMDELTA_J2000` columns, any `ASTREFEPOCH_TYPE` | +43, +46 (= the 2016→2026.5 motion) | 63 / 61 |

The last row confirms the code reading: with a FILE catalogue SCAMP reads the PM columns and ignores them.
SCAMP's own download (`-ASTREF_CATALOG GAIA-DR3 -ASTREFEPOCH_TYPE FIELDS_AVERAGE`) could not be tested: 2.15.0
reported "No VizieR server" for every mirror from this workstation. Scripts: scratchpad `scamp_test/run_test.py`
(copies the LDAC into a scratch directory first, because SCAMP writes the `.head` next to its input).

### 5.4 The `OBSDATE` column: who writes it and what reads it

`OBSDATE` is not a FITS header card; it is a per-star column in the `LDAC_OBJECTS` table of a local reference
catalogue, named by `ASTREFOBSDATE_KEY` (default `OBSDATE`, `preflist.h:90,256`).

Producers:

- NEOexchange `write_ldac` (`photometrics/catalog_subs.py:457-461`): constant 2015.5 for every star, whatever the
  data release, and attached to positions that are actually at epoch 2000.0.
- PhotometryPipeline `catalog.write_ldac` (`catalog.py:873-877`): constant 2015.0, hard-coded, not the `epoch_jd`
  column; attached to positions at 2016.0.
- SCAMP itself when `ASTREF_CATALOG` names a VizieR catalogue and `SAVE_REFCATALOG Y`: the saved LDAC uses the
  `refkey[]` columns (`astrefcat.c:56-79`: `X_WORLD`, `Y_WORLD`, `ERRA_WORLD`, `ERRB_WORLD`, `PMALPHA_J2000`,
  `PMDELTA_J2000`, their errors, `MAG`, `MAGERR`, `OBSDATE` = the catalogue epoch). Note `X_WORLD`, not
  `XWIN_WORLD`: a SCAMP-saved catalogue cannot be re-read with our `ASTREFCENT_KEYS` unchanged.

Consumers (SCAMP master `72b7e76`; 2.0.4 is the same minus the PM columns):

- `read_astrefsamples` (`astrefcat.c:1463-1475, 1553`) loads the column into `sample->epoch` (0.0 plus a warning
  if absent). The image side is `set->epoch` = `MJD-OBS`/`MJDSTART`/`DATE-OBS` + `EXPTIME`/2 (`fitswcs.c:456-496`,
  `samples.c:384-386`); the reference field itself gets `field->epoch = -1` (`astrefcat.c:1285`).
- `astrprop_fgroup` (`proper.c:550, 561`): `dt = samp1->epoch − samp->epoch` in the per-source proper-motion /
  parallax least squares, reference star included when `INCLUDE_ASTREFCATALOG Y` (default); the fractional year
  also sets the parallax factor. Runs only with `COMPUTE_PROPERMOTIONS Y` or `COMPUTE_PARALLAXES Y`.
- `merge_fgroup` (`merge.c:159-181`): weighted mean epoch and min/max per merged source, reference samples
  contributing their `OBSDATE`.
- `catout.c:290-292, 533`: epoch/epochmin/epochmax go into `MERGEDOUTCAT`/`FULLOUTCAT` (both `NONE` in our
  config and in PP's); check-plots `ASTR_OBSDATE3D`/`ASTR_REFPROP`. The XML reports `field->epoch` per image
  field only.
- `reproj_fgroup(…, propflag)` (`astrsolve.c:1650-1706`) is the one place that would move positions by
  PM × (epoch difference) before a further solve, but `propflag` is `prefs.propmotioncorr_flag`, whose config key
  `CORRECT_PROPERMOTIONS` is commented out (`preflist.h:129, 322`), so the flag is never set and the final
  reprojection (`makeit.c:518`) runs with it off. This is why `OBSDATE` and `COMPUTE_PROPERMOTIONS` never touch
  the `.head` WCS.
- Not used by: cross-identification, `astrsolve_fgroups`, clipping, the `.head` writer.
- NEOexchange and PP read nothing back from it: `get_scamp_xml_info`/`updateFITSWCS` take the `ASTRRMS` values and
  contrast figures; the `AstRefObsDate_Key` PARAM in the XML fixtures is just the config echo. (PP's
  `telescopes.py:5078` `OBSDATE|OBSTIME` is an unrelated raw-header date keyword for P60/SEDM.)

So the column has no effect on either pipeline's WCS today. When positions are propagated (5.2) it should carry the
epoch they were propagated to, so that any future SCAMP proper-motion fitting or merged-catalogue output is
self-consistent.

### 5.5 Local file versus letting SCAMP download Gaia itself

The local-file route dates from SCAMP 2.0.4, which has no Gaia support. SCAMP ≥ 2.13 can fetch `GAIA-DR3` from
VizieR itself and, with `ASTREFEPOCH_TYPE FIELDS_AVERAGE` (or `MANUAL` + `ASTREF_EPOCH`), propagate it to the
exposure epoch with error inflation — exactly the fix of 5.2, done inside SCAMP. Whether to switch:

- **It does not work today.** Every attempt in 5.3 failed with "No VizieR server at …" on four mirrors. The cause is
  reproducible and not network: VizieR 7.6.1 (all mirrors) answers HTTP 500 to a request without a `User-Agent`
  header, and SCAMP's libcurl wrapper never sets one (`src/url.c:250-256`, no `CURLOPT_USERAGENT`). `curl` on the
  URL SCAMP logs returns the catalogue; `curl -H "User-Agent:"` on the same URL returns the 500 page, whose first
  line is not `#`, which is the check at `astrefcat.c:383`. A one-line patch and a rebuild would fix it; SCAMP
  2.15.0 (2026-04-12, the latest tag) does not have it.
- **Production is on 2.0.4.** The LCO yum repo (`packagerepo.lco.gtn/repos/lcogt/8`) carries only
  `scamp-2.0.4-1.lcogt.el8`; the 2.15.0 on the workstation is a local el9 build (2026-11-04). The SCAMP route needs
  a new package in the image as well as the patch above.
- **Release lag for new Gaia releases** (SCAMP git, first commit adding the catalogue vs Gaia release):
  DR1 2 days (2016-09-16), DR2 same day (2018-04-25), EDR3 21 months (2022-09-17), DR3 15 months (2023-09-22) with
  the first tagged release containing it 2.13.1 on 2025-01-26, 31 months after DR3. Tags are infrequent (2.10.0
  2020-12, 2.13.1 2025-01, 2.14.0 2025-04, 2.15.0 2026-04). For DR4 (2026-12-02) the realistic path through SCAMP
  is a year or more plus an LCO package build; VizieR normally has the main source table within days, and our
  route needs a new VizieR ID, column check, epoch (2017.5) and MPC catalogue code — hours, not months, and it can
  be done the week DR4 appears. DR4 would also require a new entry in SCAMP's hard-coded `astrefcats[]` table
  (`astrefcat.c:192-218`), so there is no configuration-only way to point an existing SCAMP at a new catalogue.
- **Caching.** SCAMP queries VizieR once per run (`-out.max=1e8` within the field radius, a few thousand rows for
  our fields); NEOexchange runs SCAMP once per frame, so a night of 300 frames would be 300 queries where the
  current code makes one per field directory. `SAVE_REFCATALOG Y` writes the fetched stars as LDAC but with
  `X_WORLD`/`Y_WORLD` column names and no propagation on re-read (5.1), so it is not a usable cache. The local route
  caches naturally and the propagation cost is nil.
- **Selection.** SCAMP applies only `ASTREFMAG_LIMITS` and the `Dup` flag; stars without proper motions are kept
  with a 10 mas/yr × Δt error floor. Our query filters `Plx > 0` (drops two-parameter solutions), and could add
  RUWE. Both are defensible; ours is more controllable and is recorded in the file.
- **Provenance.** With a local file the catalogue name, epoch and selection are ours to record in the e92 header
  and `Frame.astrometric_catalog`; with SCAMP's download the epoch exists only in SCAMP's log.
- **Photometry is separate.** The zero-point path uses `calviacat` (`pipelines/processdata.py:610-614`) and its own
  Gaia download, so nothing else depends on the astrometric LDAC.

Conclusion: keep the local file. The missing piece is the propagation (5.2), ~15 lines in `get_vizier_catalog_table`/
`write_ldac`, after which the result is as good as SCAMP's own route (5.3: −0.4/+1.2 mas) on every SCAMP version
including the 2.0.4 in production, and the DR4 switch-over is under our control. Revisit only if LCO packages a
patched SCAMP ≥ 2.13 and a multi-frame fit (section 8, PP style) is wanted.

### 5.6 Timescale of the epoch

Gaia's `ref_epoch` J2016.0 is a Julian epoch in TCB. ERFA `pmsafe`/`starpm` take both epochs as TDB Julian dates
and proper motions "per TDB Julian year"; `epj` documents "Julian Epoch is TDB (or TT, near enough)"; astropy's
`SkyCoord.apply_space_motion` converts both times to TDB before calling `pmsafe`. Rubin converts the catalogue
epoch at ingest from its native scale (TCB for Gaia) to TAI MJD (`convertRefcatManager._epochToMjdTai`) and
propagates with `(epoch.tai − catEpoch)` in years (`loadReferenceObjects.py:1049–1053`), i.e. consistently in
TAI. Sizes: TT − UTC = 69.184 s, constant since 2017-01-01 with no leap second scheduled; TCB − TT = 24.2 s in
2026; TDB − TT ≤ 2 ms. Using UTC instead of TCB mis-states Δt by 93 s = 3 × 10⁻⁶ yr, i.e. 0.3 µas at
100 mas/yr, so the choice is one of principle: NEOexchange uses TT (the scale ERFA defines Julian epochs in,
24 s from Gaia's TCB, one existing pyslalib call with a now-constant offset) and labels `WCSREPOC` accordingly.

## 6. Rubin / LSST Science Pipelines

Source read 2026-11-06 at the `lsst` GitHub org (meas_algorithms `c86a7ac1`, meas_astrom `fced8664`, pipe_tasks
`c47dc4b0`, drp_tasks `1111cb08`, gbdes `79e8e330`, afw `dc1c6cd0`, obs_base `678a7c2f`, obs_lsst `48eba78e`,
ip_diffim `c2216910`, ap_association `e829cd19`, and others). Structural point first: solar-system detections come
from the Alert Production (prompt) pipeline, which uses only the single-frame WCS from `CalibrateImageTask`; the
global gbdes fit, stellar parallax, DCR colour terms and the turbulence model exist only in Data Release Production.

- **Reference catalogue.** `gaia_dr3_20230707` by default; LSSTCam overrides to `the_monster_20250219`, whose
  astrometric columns are Gaia DR3 passed through unchanged. The converted refcat stores `coord_ra/dec` (ICRS,
  radians, at the catalogue's own epoch), `epoch` (TAI MJD, converted per row from Gaia's `ref_epoch` in TCB
  Julian years), `pm_ra` (= μα·cosδ), `pm_dec`, `parallax`, their errors and, in format version 2, the full
  covariances (`convertReferenceCatalog.py:150-200`, `convertRefcatManager.py:375-398`). Positions are not moved at
  conversion time.
- **Proper motion.** `ReferenceObjectLoader.loadRegion/loadPixelBox` call `applyProperMotions(refCat, epoch)` on
  every load (`loadReferenceObjects.py:211-276, 1017-1080`). Linear in time, no radial-velocity or perspective
  term, no parallax: `offsets = pm × Δt(years, TAI)` applied as a great-circle arc along its bearing
  (`SpherePoint.offset`). Position errors are inflated by `pm_err × Δt` (diagonal only; "TODO DM-36979: this needs
  to incorporate the full covariance"). Single-frame passes the exposure mid-time:
  `epoch = exposure.visitInfo.date.toAstropy()` (`astrometry.py:433`). `requireProperMotion` defaults to `False` in
  single-frame (a refcat without PM columns degrades to a warning); gbdes and jointcal set it `True`
  (`gbdesAstrometricFit.py:865-866`). Stars without proper motions (Gaia 2-parameter sources, NaN in DR3) end up
  with NaN coordinates and are removed by the finite-coordinate selectors and `excludeNonPMObjects`: dropped, not
  used at catalogue epoch.
- **Parallax.** Not applied in the loader or single-frame fit. gbdes (DRP) solves a 5-parameter model per star
  (position, parallax, PM) with the observatory's barycentric position per visit and the Gaia values as a
  full-covariance prior (`Match.cpp:38-79`, `gbdesAstrometricFit.py:1268-1276, 2222-2234`); Rubin sets
  `fitProperMotion = True` (`obs_lsst/config/gbdesAstrometricFit.py`).
- **WCS model.** Single-frame: `CalibrateImageTask` retargets the fitter to `FitAffineWcsTask`
  ("assumes we have a good camera geometry", `calibrateImage.py:644-645`): a 6-parameter affine + shift per
  detector on top of the camera-geometry distortion model, unweighted least squares, up to 3 match/fit iterations,
  `maxMeanDistanceArcsec = 0.5` as a failure gate, a SIP order-5 approximation written only for FITS headers.
  DRP: gbdes per-band per-detector polynomial (order 5) → per-visit polynomial (order 7) → tangent plane, fitted
  per HEALPix pixel on isolated stars, and that WCS replaces the single-frame one.
- **Differential chromatic refraction.** None in single-frame or AP. gbdes has an optional per-visit colour term
  (`useColor`, Rubin `True`, reference g−i = 1.439; a constant 2-vector × (colour − reference)); it is explicitly
  kept out of the delivered WCS ("DCR fit should not go into the generic WCS") and written to a separate
  coefficients dataset with no consumer found. DP1 paper: "Correction for DCR … was not done for DP1".
- **Time.** `VisitInfo.date` is TAI at mid-exposure, `begin + (end − begin)/2` from `MJD-BEG`/`DATE-BEG`/`MJD-OBS`
  and `DATE-END` or exposure time (`makeRawVisitInfoViaObsInfo.py:154-164`, `VisitInfo.h:62,76`;
  LSSTCam uses `SHUTTIME`). The same instant is used for the refcat propagation, the DiaSource `midpointMjdTai`
  and the ephemeris evaluation for association; one value per detector-visit, no per-source time. Shutter-motion
  profiles can be ingested but no pipeline task applies them yet (forum, T. Jenness 2025-07: DiaSource times "will
  be corrected for the shutter motion"; DR1 promised). Reported `obsTime` is UTC.
- **Moving-object measurement.** Detected and measured on the difference image by `DipoleFitTask`; the centroid is
  `base_SdssCentroid` (the dipole fit only replaces it for mixed-sign footprints), converted to sky through the
  exposure WCS. `raErr/decErr` are the centroid covariance through the local Jacobian only, no WCS or catalogue
  term. Trails: `ext_trailedSources_Naive` reports separate `trailRa/Dec/Length/Angle` from second moments; the
  main `ra/dec` are not trail-fitted, and nothing assigns a different time to the trail centre; trails faster than
  10°/day are discarded. Association is nearest DiaSource within 1″ of the ephemeris at `visitInfo.date`.
- **MPC reporting.** The operational ADES writer is not public. Submissions seen on the MPC (station X05, 2025
  First Look) carry `astCat = Gaia2`, `rmsRA/rmsDec` ≈ 0.10–0.14″; the released 2026 ED138 PSV has 7-decimal
  degrees and UTC `obsTime` to 1 ms. The public heliolinx ADES writer hard-codes `Gaia2` and applies a manual time
  shift "to convert from TAI to UTC". Whether that tool produces the operational submissions is not verified.
- **Other.** Reference stars: PSF stars at S/N ≥ 50 (single-frame); isolated, unresolved, S/N 8–1000 for gbdes;
  no reference magnitude cut by default. Fit statistics go to the headers as `SFM_ASTROM_OFFSET_MEAN/STD/MEDIAN`.
  DRP additionally fits a Gaussian-process atmospheric-turbulence correction per visit (`fit_turbulence.py`;
  RTN-129). DP1 paper: Gaia DR3 offsets "almost all within 5 mas" against a 50 mas requirement; the 3I/ATLAS paper
  (custom extractor) finds known asteroids at −20/−34 mas from HORIZONS at image mid-time.

### 6.1 Side by side

| | NEOexchange (today) | PhotometryPipeline | SCAMP built-in (≥ 2.13, VizieR only) | Rubin single-frame | Buie `astrom` |
|---|---|---|---|---|---|
| Reference positions | Gaia DR3 at epoch 2000.0 (VizieR `RAJ2000`) | Gaia DR3 at epoch 2016.0 (VizieR `RA_ICRS`) | Gaia at catalogue epoch, optionally propagated | Gaia DR3 propagated to exposure mid-time | Gaia DR2/3 propagated to image mid-time |
| Propagation formula | none | none (`pmRA`/`pmDE` downloaded, dropped) | linear, μα*/cosδ | linear, great-circle arc | linear, μα*/cosδ |
| Stars without PM | n/a (Plx > 0 cut) | kept | kept, error + 10 mas/yr × Δt | dropped (NaN) | unspecified |
| Reference parallax | no | no | no | no (gbdes: yes) | no |
| Position error after propagation | catalogue only | catalogue only | + μ_err Δt | + μ_err Δt | not weighted |
| WCS model | linear (2m0) / TPV 3 (1m0 Sinistro) | TPV 3, all frames of a run in one fit | polynomial, any order | affine on camera model (gbdes: 5/7 poly) | linear by default, any terms |
| DCR | no | no | colour term for PM fit only | no (gbdes: optional, not in WCS) | no (paper: yes, private) |
| Mid-time | `DATE-OBS` + `EXPTIME`/2 (UTC) | `MIDTIMJD` = `DATE-OBS` + `EXPTIME`/2 (UTC), unused for the catalogue | `MJD-OBS` + `EXPTIME`/2 | begin + (end−begin)/2 (TAI) | start + exptime/2 (UTC) |
| Epoch recorded in output | no | no (`OBSDATE` = 2015.0 constant) | no | `midpointMjdTai` per source | no |



## 7. Marc Buie's IDL library

Source: `buie_idlv91.tar.gz` (2024-12-11 listing; also v8.5 of 2017-01 and v8.8 of 2022-01 for dating).

- **Reference catalogue and epoch.** Since May 2018 (`refnet.pro` "2018/05/08, MWB, added GAIA option";
  `astrom.pro` "2018/05/11, Changed to support Gaia DR2 catalog") `astrom.pro` converts the image mid-time JD to a
  decimal year (`jd2year`) and passes it as the Gaia epoch to `refnet` → external `grefnet`, whose output is
  converted by `gaiafcat`/`wrstarc`. The propagation is linear per star from the per-star catalogue epoch
  (`wrstarc.pro:108-109`: `ra = input.ra + input.rapm*(epoch-input.epoch)`, `dec = input.dec + input.decpm*…`,
  with `rapm` pre-divided by cos δ in `rdstarc.pro:171`). No parallax, no radial-velocity term, no special handling
  of stars lacking proper motions. Before 2018 (USNO-A, "UCAC", 2MASS) no proper motion was applied at all. The
  catalogue extractors (`grefnet`, `refnet`, `refnet2`) and their binary catalogues are not in the public tarball.
- **Caveat in his code.** The reference catalogue is built once per object name and reused unless `/NEWCAT`, so
  the epoch is that of the first image reduced in a directory: harmless within a night, stale if the directory is
  reused across epochs. Exactly the trap our per-directory cache has.
- **Frame.** Everything is in catalogue (ICRS/J2000) astrometric coordinates through a gnomonic projection
  (`astrd2sn`/`astsn2rd`, "Smart p283"). No aberration, nutation, precession-to-date or refraction step in the
  astrometry chain; differential effects are left to the fitted terms.
- **Plate model.** `astsolve.pro`: separate, unweighted SVD least-squares fits of ξ(x,y) and η(x,y) over a
  user-chosen term list (`astterms.pro`: constant, linear, quadratic, cubic …, Chebyshev/Legendre families), default
  `['CONST','X','Y']`, iterated with 3σ clipping; the 'R' term is "not encouraged". Star rejection: FWHM outliers,
  magnitude error > 0.1, peak above a saturation level, nearest-neighbour matching within 4.3 px, coverage check in a
  3×3 grid, whole fit abandoned if the worst residual exceeds 3″. Fit scatter is printed and returned but not
  written to the output files; the FITS keywords he writes carry no scatter, catalogue name or epoch. The Leucus
  paper (Buie et al. 2021, PSJ 2, 202, App. B): "This astrometric solution is a simple linear fit. There are no
  measurable higher-order terms."
- **Refraction / DCR.** Nothing applied in the public pipeline. Stand-alone `refcorr.pro` (2019) and
  `astwave.pro` (2021, photon-weighted pivot wavelength with a reddened-Sun option) exist with no callers. The Leucus
  paper reports a differential refraction correction "relative to the mean wavelength of the comparison stars", up
  to −40 mas, mean −15 mas in VR; that code is not public.
- **Time.** `parsekey.pro:416-419`: `info.jd = jd + exptime/2/86400`. No shutter correction; UTC throughout the
  IDL (TT handling is inside the external `geteph`).
- **Target measurement.** Two-pass first-moment centroid in a circular aperture (`basphote`/`centrod`), same
  routine and aperture for stars and target; no trailed-source model for ground-based data. Later papers use PSF
  fitting and stacks (Arrokoth: Buie et al. 2020, AJ 159, 130; Leucus 2021) and are not in the tarball.
- **Output.** His own `.ast` format (JD to 1e-5 d, RA to 0.0001 s, Dec to 0.001″) and a Bowell-format `.ted`;
  no MPC 80-column/ADES writer and no catalogue code in the public library.
- **Published practice.** Buie et al. 2020 §2/§5: pre-Gaia catalogues "did not have useful proper motion
  information. To overcome this limitation, we used mean apex proper motion corrections (Gwyn 2014)… inadequate
  for the positions of the occultation stars themselves"; with DR2, "corrected for proper motion to the epoch of the
  images", and the same catalogue used for both the image astrometry and the occultation star. Occultation target
  stars additionally get parallax and the DR3 bright-star PM-bias correction (`paracorr.pro`, Cantat-Gaudin &
  Brandt 2021).

## 8. PhotometryPipeline (Mommert)

Source: local checkout `~/git/photometrypipeline` at `8514d04` (2025-09-03, "Add basics of LCO FTN MuSCAT3 support").
The uncommitted edits there touch `telescopes.py`/`pp_run.py` only; the catalogue code is as committed.

- **Reference catalogue and epoch.** `catalog.download_catalog` for `'GAIA'` (`catalog.py:331-385`) queries VizieR
  `I/355/gaiadr3` for `RA_ICRS`, `DE_ICRS`, `e_RA_ICRS`, `e_DE_ICRS`, `pmRA`, `pmDE`, `Epoch` and the G/BP/RP
  magnitudes, renames `RA_ICRS`→`ra_deg`, and adds a constant `epoch_jd` = 2457389.0 (2016.0; the DR2 value
  2457206.375 is left commented out — commits `d099033` 2022-09 and `21c4453` 2025-09). The proper-motion columns
  are downloaded and carried in `self.data` but nothing reads them; the TBD comment at `catalog.py:382-384` still
  says "implement propor motion handling for DR2". `TGAS` (`catalog.py:423-461`) is the same with "implement pm
  progragation" as its TBD. So PP's reference positions are at the Gaia catalogue epoch, not the exposure epoch.
- **LDAC written for SCAMP.** `catalog.write_ldac` (`catalog.py:823-895`) writes only `ra_deg`, `dec_deg`,
  `e_ra_deg`, `e_dec_deg`, `mag` (as `XWIN_WORLD`, `YWIN_WORLD`, `ERRAWIN_WORLD`, `ERRBWIN_WORLD`, `MAG`), a
  constant `MAGERR` = 0.01 and a constant `OBSDATE` = **2015.0** (hard-coded, not `epoch_jd`; harmless only because
  `COMPUTE_PROPERMOTIONS N`). No `ERRTHETAWIN_WORLD` column is written although the config names it; no PM columns.
  The position errors are the real per-star Gaia values converted to degrees, so SCAMP's weighting is sensible.
- **Registration.** `pp_register.register` (`pp_register.py:77-246`): one SCAMP call per run over all frames'
  LDACs, `-ASTREF_CATALOG FILE -ASTREFCAT_NAME GAIA.cat` plus the flag masks; the catalogue is downloaded fresh
  each run (`GAIA.cat` in the working directory, overwritten), radius from `toolbox.skycenter` over all frames +
  `reg_search_radius`, magnitude limit `reg_max_mag`, row limit 100000, no parallax or quality cuts. Success is
  judged on SCAMP's `AS_Contrast`/`XY_Contrast` ≥ 2.5; `AstromSigma_Reference` and the χ² are kept for the
  diagnostics only. The `.head` is parsed into the FITS header (`pp_register.py:340-370`) together with
  `REGCAT` = catalogue name; nothing records the epoch.
- **SCAMP config.** `setup/lcosin.scamp` etc. are the SCAMP 2.0.4 default with `PROJECTION_TYPE TPV`,
  `DISTORT_DEGREES 3`, `STABILITY_TYPE INSTRUMENT`, `ASTRINSTRU_KEY L1FILTER`, `CROSSID_RADIUS 2.0`,
  `ASTRCLIP_NSIGMA 1.5`, `ASTR_ACCURACY 0.01`, `ASTREFMAG_LIMITS -99,21`, `COMPUTE_PARALLAXES N`,
  `COMPUTE_PROPERMOTIONS N`, `CORRECT_COLOURSHIFTS N`. Fitting all frames of a night together with a shared
  instrument distortion is the main thing PP does that NEOexchange does not; it is also why the 2m0 fits there are
  cubic rather than linear.
- **Time.** `pp_prepare` writes `MIDTIMJD` = `DATE-OBS` (+ `TIME-OBS`) + `EXPTIME`/2 as a UTC JD
  (`pp_prepare.py:268-286`); `pp_register` reads it only to confirm `pp_prepare` has run (`pp_register.py:70`).
  The mid-time and the proper motions are therefore both already in memory inside `register()` when `GAIA.cat`
  is written; propagating is a few lines in `download_catalog` (take `MIDTIMJD` as an argument, apply
  `pmRA`/`pmDE` × (t − 2016.0) to `ra_deg`/`dec_deg`, set `OBSDATE` from it).
- **Net effect.** For data taken in 2026 the WCS is tied to the sky of 2016.0: offset −μ̄_field × 10.5 yr instead
  of our 26.5 yr. On the Didymos field that is ≈ +45 mas (the 2016.0 + PM variant in section 5.3 is exactly PP's
  input and gave +42.7/+46.2 mas). Smaller than NEOexchange's 0.17″ but the same class of error and growing at
  ~4 mas/yr on this field; it is not removed by the MPC debiasing either.

## 9. Error budget beyond the epoch (this dataset)

| Term | Size on 2026-07-12 (2m0 MuSCAT4, 0.268″/px) | Note |
|---|---|---|
| Reference epoch (the bug) | 170 mas, systematic | section 2 |
| Linear WCS vs real distortion along the target's track | ±20 mas (predicted dx −0.53 → −0.37 px across the chip) | `DISTORT_DEGREES 1` on 2m0; a cubic/TPV fit would absorb it |
| Differential chromatic refraction, g′ vs z_s, airmass ≤ 1.42 | < 13 mas, not detected | would be larger for bluer targets / higher airmass |
| Timing | < 2–3 s ⇒ < 20 mas at 0.5″/min | `DATE-OBS` + `EXPTIME/2`; no shutter model |
| Reference-star parallax | ≈ 1 mas | ignored by everyone surveyed |
| Ephemeris (HORIZONS 3σ) | 1 mas | |
| Centroid of a trailed target vs windowed star centroids | tens of mas at 6.6 px trail | the +19 mas along-track residual may be this |

## 10. Recommendations for NEOexchange

1. **Done (4.1).** Fix `get_vizier_catalog_table`/`write_ldac` per section 5.2; the cache is keyed on epoch.
2. **Done (4.1).** `WCSREPOC` in the e92 header, `Frame.astrometric_epoch`, and the `WCSRDRES` > 0.1″ warning in
   the pipeline log.
3. **Done.** `COMPUTE_PROPERMOTIONS N` in both SCAMP configs.
4. **Open.** Existing e92 frames are only corrected by re-running the astrometric fit. For MPC-reported astrometry the offset
   is −μ̄_field × (t − 2000), i.e. field dependent; a per-field correction could be computed from the cached
   catalogue and the Gaia proper motions without re-reducing, if that is ever wanted.
5. **Done (unit tests in `photometrics/tests/test_catalog_subs.py`, `test_external_codes.py`,
   `core/tests/`, `pipelines/tests/`; the end-to-end check in 4.1 is a scratch script, not a test).**
6. **Open.** Re-fit the Hera/DART e92 frames of 2026 (and any astrometry already reported to the MPC from them)
   once the change is deployed on apophis2.

## 11. Files

- Analysis scripts and the Gaia DR3 table for the field: `/data/tlister/hotpants_demo/dia_crosscheck/`
  (`didymos_xy.py`, `gaia_fetch.py`, `frame_offset.py`, `local_offset.py`, `centroid_groups.py`,
  `gaiadr3_field.fits`, `65803_20260712_E10_e92_xy.txt`).
- SCAMP experiment: `/data/tlister/hotpants_demo/dia_crosscheck/scamp_test/run_test.py` (variants A/B/C/N; expects
  `../gaiadr3_field.fits`).
- PhotometryPipeline was read from the local checkout `~/git/photometrypipeline` (`8514d04`).
- Code reading: the SCAMP, LSST and Buie sources were cloned/downloaded read-only into a session scratchpad (lost on
  reboot); the commit hashes and tarball versions above identify what was read. Key citations were spot-checked
  against the sources before this note was written.
