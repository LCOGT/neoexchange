# BHTOM "CCDPhot" as a third zeropoint cross-check for the LCO/MuSCAT3 Didymos frames

Assessment date 2026-11-02. Question asked: can BHTOM's CCDPhot reduction code serve as a third, independent
cross-check of the NEOexchange (calviacat/PS1) and photometrypipeline (PS1→SDSS) zeropoints for Block 35906
(COJ 2 m, MuSCAT3 g′r′i′z_s, 2026-07-12), and does it still work while CDS VizieR is down?

Research was done by web/document/code reading (no uploads, no accounts created). Legend: 
 - **[V]** = verified directly (page, code or PDF read, or a live network probe on 2026-11-02 21:55–22:08 UTC);
- **[I]** = inferred;
- **[NF]** = not found. 

The IDIA VizieR / Gaia TAP / CDS probes in §9 were re-run independently from the
workstation at the time of writing: IDIA served `I/360/syntphot` rows for a test cone, CDS gave no response,
and the Gaia TAP sync endpoint returned an HTML page to a hand-built query (so "probably up, not verified").

## Verdict (short)

**Not viable within a week, and of limited value for this purpose even with time.** CCDPhot is a closed,
server-side pipeline: it cannot be run locally; the COJ 2 m/MuSCAT3 camera would need admin approval; the
Hera frames would have to be uploaded to a third-party server whose terms assert ownership of derived
products, broad download rights for all registered users and co-authorship expectations; moving targets are
not supported; and the output is a zeropoint relative to an undocumented DAOPHOT instrumental-magnitude
convention with **no per-star calibrated catalogue**, in SDSS g,r,i,z (no z_s, no PS1 system). The cheapest
genuinely independent third check is to compute a **Gaia DR3 Synthetic Photometry (GSPC) zeropoint locally**
(§10), which is the same calibration system BHTOM uses, from the IDIA VizieR mirror or the ESA Gaia archive.

## 1. What BHTOM CCDPhot is

- **BHTOM** = Black Hole Target Observation Manager, Warsaw University Astronomical Observatory (Wyrzykowski,
  Mikołajczyk, Kotysz, Zieliński). bhtom.space redirects to https://bh-tom2.astrouw.edu.pl/ (server moved
  2026-03-25). **[V]**
- **CCDPhot** is BHTOM's *internal, server-side* FITS-processing pipeline, not a user-facing program.
  Mikołajczyk et al. 2025 (RMxAC 59, 167–172, DOI 10.22201/ia.14052059p.2025.59.26 — the citation BHTOM asks
  for) describes it as "CCDPhot based on BASH shell and Python scripts, IRAF/PyRAF, SExtractor, SCAMP, DAOPHOT
  and WCSTools"; the 2024 BHTOM-IT workshop deck adds "JDAY, SWARP, CDS CLIENT, PSFEX and many more", and says a
  successor **CCDPhot2** "will work only in the Docker environment" (their internal infrastructure). **[V]**
- Pipeline steps (workshop deck + 2025 paper): (1) standardise FITS headers using a per-observatory
  `obs.info` template; (2) build astrometric reference catalogues (URAT-1, UCAC-4, USNO-B1/NOMAD-1, 2MASS);
  (3) SExtractor+SCAMP astrometry, final solution on Gaia DR3 ("last chance astrometry: nova.astrometry.net");
  (4) automatic PSF model; (5) DAOPHOT aperture+PSF photometry of *all* stars; (6) output an ASCII "photometry +
  astrometry of all stars" file (the `.dat` CPCS input) and a `*-ccdp.fits`. Photometric standardisation is then
  done by **CPCS** (Cambridge Photometric Calibration Server, originally Koposov & Wyrzykowski 2013; CPCS 2.0 =
  Zieliński et al. 2020, arXiv:2006.05160, "built on the CCDPhot package"). **[V]**
- Papers: Mikołajczyk et al. 2025 (RMxAC); Zieliński et al. 2020 (arXiv:2006.05160); usage papers: Gaia20bof
  (arXiv:2405.02223), 3I/ATLAS with BHTOM (arXiv:2603.01383, A&A 2026). No dedicated CCDPhot paper exists
  (cited as "in prep." until 2025). **[V]**
- **Licence:** no public CCDPhot repository, so no licence **[NF]**. GitHub org BHTOM-Team has `bhtom2` (no
  LICENSE file; API reports license=null) and `bhtom_base` (GPL-3.0). The docs claim CPCS and the Upload Service
  are MIT, but the referenced repos `BHTOM-Team/cpcsv2` and `BHTOM-Team/upload-service` return 404 (private or
  non-existent). **[V]**

## 2. Standalone or server-only?

- **Server-only.** Checked: PyPI (`pip download --no-deps` for `ccdphot`, `ccdphot2`, `bhtom-ccdphot`,
  `bhtom_ccdphot`, `bhtom`, `bhtom2`, `cpcs` → "No matching distribution"); GitHub (`BHTOM-Team/ccdphot`,
  `CCDPhotService`, `ccdphotsvc` → 404; global repo search for "ccdphot" finds only unrelated
  `MickaelRigault/ccdphot`, `vkudak/ccd_phot`); Docker Hub search for "ccdphot" → empty. The author's own GitHub
  (astromiki) has no CCDPhot repo. **[V]**
- The only way to run it: upload FITS to BHTOM. Prerequisites (2026.3 Visual Manual + API doc): registered
  account (admin-activated), API token from `POST /api/token-auth/`, a *target* existing in BHTOM, and a
  *registered and admin-approved observatory + camera* ("fill all the details, attach example fits files, wait
  for the approval"; each camera gets an ONAME used in the API). **[V]**
- Upload: web GUI (max 5 files per upload) or `POST https://uploadsvc2.bh-tom2.astrouw.edu.pl/upload/` with
  header `Authorization: Token <tok>` and form fields `target`, `observatory` (ONAME), `filter` (e.g.
  `GaiaSP/any`), `data_product_type=fits_file`, `dry_run`, `comment`, `match_dist`, file in `files`. Reference
  scripts: `Documentation/documentation_scripts/send_fits_to_bhtom.py`, `upload_files_script.py`,
  `get_calib_res.py` in github.com/BHTOM-Team/bhtom2 (dependency: Python 3 + `requests` only). **[V]**

## 3. Inputs and outputs

- **Input:** bias/dark/flat-corrected FITS (`.fits`, `.fits.fz`, `.fits.gz` accepted since issue #336, 2026-05).
  **WCS is not required** — CCDPhot solves astrometry itself (SExtractor/SCAMP + Gaia DR3), though an existing
  BANZAI WCS presumably helps the initial match **[I]**. Header keywords are mapped per observatory via the
  `obs.info` template; the `CCDPhotJob` model records what it parsed: `fits_object, fits_ra, fits_dec, fits_mjd,
  fits_hjd, fits_exp, fits_filter, fits_origin, fits_observat, fits_telescop, fits_instrume, fits_observer,
  fits_pixscale, fits_binning, fits_dateobs`. **[V]**
- **Per-file results** (model `Calibration_data`, returned as JSON by `POST /calibration/get-calibration-res`
  with `filename`/`calibid` arrays, optional base64 PNG `plot` and `ccdphot_results`): `mag`, `mag_error`
  (target), **`zeropoint`**, **`scatter`** (ZP scatter), **`npoints`** (stars used), `outlier_fraction`,
  `best_filter`, `survey`, `match_distans`, `processing_time`, `calibration_log` (URL), `cpcs_results` (JSON).
  The CCDPhot tab adds FWHM_X/Y/AV, SEEING, AIRMASS, PHOTFLAG, NUMSTARS, MOON*/SUN*, PIPEVER, GLIM (limiting
  mag). **[V]**
- **No formal ZP uncertainty field** — only `scatter` and `npoints` (scatter/√npoints can be formed). **[V]**
- **Per-star catalogue:** the instrumental photometry of all detected stars (CCDPhot `.dat`, "SExtractor
  format": MAG, MAGERR, RA, Dec) is downloadable (`POST /common/api/downloadPhotometryFile/` by DataProduct id,
  or the "photometry file" link on the data-product page). A **calibrated per-star catalogue with
  catalogue-vs-instrumental magnitudes is NOT exposed** — it appears only in the calibration PNG; the CPCS
  catalogue-browser view is staff-only (`CpcsCatalogData` checks `is_staff`); issue #311 (open, 2025-11)
  proposes returning all intermediate CCDPhot products. Light-curve download
  (`POST /targets/download-photometry/`) gives `MJD;Magnitude;Error;Facility;Filter;Observer` for the target
  only. **[V]**
- **Caveat for a ZP comparison:** the ZP is defined relative to DAOPHOT PSF instrumental magnitudes whose
  normalisation (exposure time, aperture correction, DAOPHOT magnitude constant) is undocumented, so the
  *number* will not be directly comparable to NEOexchange's or PhotPipe's ZP. A like-for-like check would have
  to go through calibrated magnitudes of common field stars, which BHTOM does not export. **[I, based on V]**

## 4. Reference catalogues, photometric systems, filters, colour terms

- Active catalogues (`bhtom2/management/commands/add_catalogs.py`, 2026.3 manual): **GaiaSP** = Gaia DR3
  Synthetic Photometry (GSPC) in **SDSS ugriz and Johnson-Cousins UBVRI** (filters
  `GaiaSP/u,g,r,i,z,U,B,V,R,I,any,ugriz,UBVRI`); **GaiaDR3/G,GBP,GRP,any** (added Dec 2024, issue #231);
  **2MASS/J,H,K,any**. SDSS, APASS, OGLE3, DECAPS entries exist but `isActive=False`. **No Pan-STARRS system,
  no ATLAS-REFCAT2.** The GSPC columns used are `g_sdss_mag, r_sdss_mag, i_sdss_mag, z_sdss_mag, *_jkc_mag`
  (issue #213). **[V]**
- Filter naming: you *force* a catalogue filter (`GaiaSP/g`, `GaiaSP/ugriz`, …) or let `GaiaSP/any`/Auto pick
  the lowest-scatter band; the FITS `FILTER` keyword is recorded but the standardisation band is the catalogue
  band you choose. For MuSCAT3 g′ r′ i′ → `GaiaSP/g,r,i`; **z_s has no match — `GaiaSP/z` is SDSS z, so expect a
  systematic offset for z_s.** **[V for naming; I for the z_s offset]**
- Method: CPCS fits a linear relation between instrumental and catalogue magnitudes of matched field stars
  (match radius default 2″, configurable), keeping the lowest-scatter catalogue/filter in auto mode (CPCS manual
  2016; issue #213 refers to fitted "slope and zero point"). The 2025 paper says "zero-point calibration and
  colour term application" and the 3I/ATLAS paper says GaiaSP "provides color-corrected synthetic magnitudes
  appropriate for PSF photometry" — i.e. colour handling comes mainly from using GSPC in the target system;
  details of any explicit colour term are not published. Magnitudes are AB (Gaia20bof paper). **[V quotes; I on
  colour-term mechanics]**
- GSPC depth: XP spectra/GSPC exist only for G ≲ 17.65; on a 9′×9′ MuSCAT field this still gives tens of
  stars at typical Didymos latitudes but fewer than PS1. **[I]**

## 5. Where the catalogue comes from at run time (VizieR dependence)

- **Photometric calibration does NOT use VizieR.** CPCS reads GaiaSP/2MASS/GaiaDR3 from the **Cambridge Whole
  Sky Database (WSDB, Koposov; PostgreSQL with q3c, host `*.ast.cam.ac.uk`)** via
  `bhtom2/external_service/connectWSDB.py`, and BHTOM keeps its own **"WSDB cache"** (a 0.5° cone downloaded
  when a target is created) in Warsaw; calibrations query the cache (architecture.md, overview deck "WSDB 0.5
  deg radius data downloaded to cache (GaiaSP, 2MASS) for calibration", issues #231, #295, #216). Issue #231
  even notes "CDS/Vizier gives different values of these errors!!" as a reason to query WSDB directly. **[V]**
- **Astrometric stage:** the source of CCDPhot's URAT-1/UCAC-4/USNO-B1/NOMAD-1/2MASS reference catalogues is
  undocumented; the workshop deck lists "CDS CLIENT" among CCDPhot's tools and SCAMP's online `ASTREF_CATALOG`
  retrieval defaults to VizieR, so **the astrometric step plausibly depends on CDS** (fallback
  nova.astrometry.net). Not verifiable from outside. **[I]**
- Nothing is user-configurable (server-side). No BHTOM status notice about VizieR exists on the About/news page
  (latest entries: 2026-03-25 server move, 2025-09-29 new CCDPhot server). **[V]**

## 6. Moving targets

- Not supported natively. Uploads are attached to a fixed-RA/Dec BHTOM *target*; CPCS measures "the target"
  at those coordinates (within the match radius) or reports an upper limit. The 3I/ATLAS paper states "BHTOM
  currently supports observation requests for non–solar system targets" and used the comet as a stress test;
  issue #311 (open) lists "moving objects with not well known ephemeris" as a *future* science case. **The
  field ZP is still computed per frame regardless**, so for a ZP-only check the target magnitude can be ignored
  (or one target per frame could be created at the ephemeris position — clumsy). **[V]**

## 7. LCO / MuSCAT in BHTOM

- LCO 0.4 m and 1 m data are routinely processed ("LCO-40cm", "LCO-1m", "CMOS-LCO-40cm" examples; "25% from
  LCO network (proposal)" of ~85k images/yr in the 2024 AstroColibri deck; 3I/ATLAS paper: LCO 0.4 m/1 m at
  COJ, CPT, LSC, OGG, TFN, BANZAI-reduced, run through BHTOM; Gaia20bof: LCO 1 m g′/i′). **[V]**
- **LCO 2 m / MuSCAT3 / MuSCAT4: not found anywhere** (papers, decks, code search for "MuSCAT", "Las Cumbres",
  "Siding Spring", "Haleakala" in BHTOM-Team repos). The observatory list API needs a token
  (`{"detail":"Authentication credentials were not provided."}`), so whether a 2 m/MuSCAT camera is already
  registered could not be checked; if not, it must be registered (details + example FITS) and admin-approved.
  **[V/NF]**

## 8. Practicalities

- Client: Python 3 + `requests`; no astropy/photutils coupling, so irrelevant to the 3.9/3.11 and astropy 5/6
  pins. Server internals (IRAF/PyRAF, DAOPHOT) are theirs. **[V]**
- Runtime: not documented per frame; CPCS 2.0 advertises "science-ready photometry within minutes"; 2024
  throughput "up to 5,000 images per week"; a new CCDPhot server (2025-09) was launched because "queues should
  be much shorter". Expect minutes-to-hours latency, queue dependent. **[V]**
- Registration: account (admin activation), token, observatory+camera approval, target creation (needs
  RA/Dec; a "non-public" target option is implied by the T&Cs). **[V]**
- **Data sharing — flag for Hera:** Terms and Conditions (Documentation/terms_and_conditions.pdf): §2.3
  "higher-level data products extracted from the original uploaded data … remains the property of BHTOM"; §4.1
  "All registered users may download the products provided by BHTOM"; §3.1 public target name/coords visible to
  all users (§3.2 non-public: visible to admins); §6.2 "users agree to include BHTOM builders as co-authors"
  when BHTOM products are used in publications. In code, `get-calibration-res` returns "It's not your data" to
  non-owners, but light-curve points on a target are downloadable by any registered user. Mitigation:
  `dry_run=True` runs CCDPhot+CPCS but "does not store datapoints in BHTOM database" (uploaded FITS are purged
  after `DELETE_FITS_FILE_DAY=7` per the env template) — whether dry-run calibration results remain
  retrievable by API afterwards is **[NF]**. Uploading proprietary Hera frames to a third-party server, with
  BHTOM claiming ownership of derived products and expecting co-authorship, needs a team decision before any
  upload. **[V]**

## 9. CDS VizieR status (2026-11-02), and where GSPC is available

- Probes 21:55–22:08 UTC (curl, 12–15 s timeouts) **[V]**:
  - `vizier.cds.unistra.fr`, `vizier.u-strasbg.fr`, `tapvizier.cds.unistra.fr`, `simbad.cds.unistra.fr`,
    `cds.unistra.fr`, `cdsarc.cds.unistra.fr` — **TCP connect timeout (down)**.
  - `vizier.cfa.harvard.edu` — **HTTP 502 Bad Gateway** (it proxies/redirects to CDS, so it is not an
    independent mirror — also reported in mwcraig/bandaid#169).
  - `vizier.nao.ac.jp`, `vizier.hia.nrc.ca` — **timeout**.
  - `vizier.idia.ac.za` — **HTTP 200**, and **serves GSPC: `I/360/syntphot`** (cone query returned rows with
    `Source, gmag, rmag, imag, zmag`; VizieR 7.6.1). Re-confirmed from the workstation at the time of writing.
    Use the **ASU query endpoint**, not the interactive form pages (those fetch catalogue metadata and the
    catalogue-search index from the CDS master and hang while it is down):
    `https://vizier.idia.ac.za/viz-bin/asu-tsv?-source=I/360/syntphot&-c=<ra>%20<dec>&-c.rm=<arcmin>&-out.max=10000&-out=Source,RA_ICRS,DE_ICRS,gmag,gFlag,Fg,e_Fg,rmag,rFlag,Fr,e_Fr,imag,iFlag,Fi,e_Fi,zmag,zFlag,Fz,e_Fz`
    (`-c` in degrees). Requesting `E(BP/RP)corr` by name in `-out` returned an empty result on this mirror;
    use `-out.all` if C\* is wanted.
  - ESA Gaia archive TAP `gea.esac.esa.int/tap-server/tap` — reported **up** by the research pass;
    `gaiadr3.synthetic_photometry_gspc` works joined to `gaiadr3.gaia_source` for ra/dec (5-row test query).
    Columns: `{u,g,r,i,z}_sdss_{flux,flux_error,mag,flag}`, `{u,b,v,r,i}_jkc_*`, `y_ps1_*`,
    `f606w/f814w_acswfc_*`, `c_star`. **No PS1 griz in GSPC — only y_PS1** (and the arXiv v3 note warns of an
    error in the y_PS1 values). A later hand-built sync query from the workstation returned an HTML page, so
    treat the TAP route as unverified until exercised with astroquery.
  - GAVO `dc.g-vo.org/tap` — up, has `gaia.dr3lite` but **no GSPC table**.
  - MAST Pan-STARRS catalogs API (`catalogs.mast.stsci.edu/api/v0.1/panstarrs/dr2/mean`) — **HTTP 200**;
    ATLAS-REFCAT2 at `archive.stsci.edu/prepds/atlas-refcat2/` — reachable (302).
- **Official CDS notice** (the only one; the CDS web news feed is on the unreachable hosts): post on the CDS
  Facebook page dated 2026-10-28,
  https://www.facebook.com/CDSportal/posts/pfbid02VYHUF2Sv76SshaR29psMYhuLCxYaoy1HoAL5UtPZBiDpDRsVmx65vMHRPBSWWLFil
  (text supplied by TL 2026-11-02) **[V]**:
  > CDS is experiencing a cybersecurity incident within its network of servers located in Strasbourg. Our teams
  > are taking steps to assess and mitigate the issue. This includes taking some systems offline to help protect
  > them. As a consequence, access to SIMBAD, VizieR, Aladin image surveys, X-Match and other services hosted on
  > our main site is currently degraded. […] In the meanwhile, you can try to use mirrors of our services:
  > SIMBAD at IDIA https://simbad.idia.ac.za/ and CfA https://simbad.cfa.harvard.edu/simbad/ ; VizieR at IDIA
  > https://vizier.idia.ac.za/viz-bin/VizieR , China-VO http://vizier.china-vo.org/viz-bin/VizieR , NAOJ
  > http://vizier.nao.ac.jp/viz-bin/VizieR and CfA https://vizier.cfa.harvard.edu/viz-bin/VizieR .

  So the cause is a **cybersecurity incident with systems deliberately taken offline**; the "patching the PHP
  CVE-2026-109618/109619" explanation circulating in user reports (m-samland/spherical PR #262) is unconfirmed
  speculation. No restoration ETA was given. Of the four VizieR mirrors CDS lists, only **IDIA** actually served
  `I/360/syntphot` from here: CfA gave HTTP 502, NAOJ timed out, and China-VO (probed 2026-11-02 after the post
  was seen) answers its front page (HTTP 200, 1.3 s) but a `asu-tsv` cone query on `I/360/syntphot` hung for 40 s
  with no bytes — presumably it, like the interactive form pages on IDIA, still proxies to Strasbourg for that
  catalogue. User-report timeline: partial failures from 2026-10-20 ("The database is not currently reachable"
  with HTTP 200), all CDS hosts timing out from ~10-28/29 (mwcraig/bandaid#169, lgriffin/SDP#107, Cloudy Nights,
  AAVSO forum). **[V]**
- GSPC VizieR ID: **I/360/syntphot** (within "Gaia DR3 Part 6. Performance verification"). **[V]**

## 10. Recommendation

(a) **Not realistically within a week as a third independent zeropoint check**, for the reasons in the verdict
above. (b) Main blockers: proprietary-data policy; approval latency; non-comparable ZP convention; no per-star
output; moving target unsupported; z_s unmatched; possible hidden CDS dependence in the astrometric stage.
(c) **Cheapest genuinely independent third check: compute a Gaia DR3 GSPC zeropoint locally** — pull
`I/360/syntphot` for each field from the IDIA mirror (or `gaiadr3.synthetic_photometry_gspc` JOIN
`gaia_source` from the ESA Gaia TAP once verified), cache per field as is already done for Gaia DR3 astrometry,
use `{g,r,i,z}_sdss_mag` with the flag and `c_star` cuts, and fit the ZP against the existing NEOexchange 6 px
aperture photometry of the same field stars from the e92 LDACs. This is exactly the calibration system BHTOM
uses, so it reproduces the "CCDPhot-style" reference without BHTOM, and it is a different catalogue and
photometric system from the PS1-based calviacat and PhotPipe fits. Caveats: GSPC stops at G ≲ 17.65 (fewer
stars than PS1), it is SDSS not PS1 (a few-hundredths systematic, especially for z_s), and it needs colour/flag
handling. ATLAS-REFCAT2 (local copy via MAST) is a possible fourth check with different systematics, but is
PS1-derived and so less independent than GSPC.

(c) was prototyped the same day on the 86 r′ frames of Block 35906: the GSPC zeropoint is −0.0048 mag from the
NEOx PS1 zeropoint with a frame-to-frame spread of 0.0006 mag — see `2026_07_12_zeropoint_analysis.md` §9.

## Sources

- BHTOM about/news: https://bh-tom2.astrouw.edu.pl/about/ (bhtom.space redirects here)
- BHTOM GitHub org: https://github.com/BHTOM-Team ; bhtom2 repo https://github.com/BHTOM-Team/bhtom2 ;
  API doc https://github.com/BHTOM-Team/bhtom2/blob/bhtom2-dev/Documentation/DocumentationAPI.md ;
  architecture https://github.com/BHTOM-Team/bhtom2/blob/master/Documentation/architecture/architecture.md ;
  CPCS service README https://github.com/BHTOM-Team/bhtom2/blob/master/Documentation/cpcs-service/README.md ;
  upload scripts https://github.com/BHTOM-Team/bhtom2/tree/master/Documentation/documentation_scripts ;
  Terms & Conditions https://github.com/BHTOM-Team/bhtom2/blob/master/Documentation/terms_and_conditions.pdf ;
  2026.3 Visual Manual https://github.com/BHTOM-Team/bhtom2/blob/master/Documentation/2026.3-BHTOM2-Visual-Manual.pdf
- bhtom2 code: `bhtom2/management/commands/add_catalogs.py`, `bhtom2/bhtom_calibration/models.py`,
  `bhtom2/bhtom_calibration/views.py`, `bhtom2/bhtom_dataproducts/views.py`,
  `bhtom2/external_service/connectWSDB.py`, `settings/.bhtom.env.template` (all under
  https://github.com/BHTOM-Team/bhtom2); `CCDPhotJob` in
  https://github.com/BHTOM-Team/bhtom_base/blob/master/bhtom_dataproducts/models.py
- bhtom2 issues: #213 https://github.com/BHTOM-Team/bhtom2/issues/213 ; #231
  https://github.com/BHTOM-Team/bhtom2/issues/231 ; #287 https://github.com/BHTOM-Team/bhtom2/issues/287 ; #295
  https://github.com/BHTOM-Team/bhtom2/issues/295 ; #311 https://github.com/BHTOM-Team/bhtom2/issues/311 ; #318
  https://github.com/BHTOM-Team/bhtom2/issues/318
- Mikołajczyk et al. 2025, RMxAC 59, 167:
  https://astronomia.unam.mx/journals/rmxac/article/view/ia.14052059p.2025.59.26
  (DOI https://doi.org/10.22201/ia.14052059p.2025.59.26)
- Zieliński et al. 2020, CPCS 2.0: https://arxiv.org/abs/2006.05160
- CPCS manual 2016: https://www.astrouw.edu.pl/~wyrzykow/manualCPCS2016.pdf
- BHTOM-IT 2024 workshop decks: https://www.astrouw.edu.pl/~wyrzykow/BHTOM-IT-2024/BHTOM-IT-Workshop_PM.pdf ;
  https://www.astrouw.edu.pl/~wyrzykow/BHTOM-IT-2024/BHTOM-IT-overview-LW.pdf
- AstroColibri 2024 BHTOM talk:
  https://indico.ijclab.in2p3.fr/event/10545/contributions/34606/attachments/23950/34803/2024.09-AstroColibri-BHTOM.pdf
- RAPID 2026 BHTOM talk: https://conference.ipac.caltech.edu/rapid-hotwiring2026/talks/JMajumdar_talk_rapid2026.pdf
- Zieliński GSAW2020 hands-on: https://www.astrouw.edu.pl/~wyrzykow/GAIA/GSAW2020/PawelZielinski-handson.pdf
- 3I/ATLAS with BHTOM: https://arxiv.org/html/2603.01383v1 ; A&A version
  https://www.aanda.org/articles/aa/full_html/2026/10/aa59913-26/aa59913-26.html
- Gaia20bof (BHTOM/CCDPhot usage, LCO): https://arxiv.org/html/2405.02223
- Gaia DR3 synthetic photometry paper: https://arxiv.org/abs/2206.06215 ; GSPC data model
  https://gea.esac.esa.int/archive/documentation/GDR3/Gaia_archive/chap_datamodel/sec_dm_performance_verification/ssec_dm_synthetic_photometry_gspc.html ;
  Gaia TAP https://gea.esac.esa.int/tap-server/tap
- VizieR mirrors probed: https://vizier.cds.unistra.fr/viz-bin/VizieR ; https://vizier.cfa.harvard.edu/viz-bin/VizieR ;
  http://vizier.china-vo.org/viz-bin/VizieR ;
  https://vizier.idia.ac.za/viz-bin/VizieR (I/360 landing https://vizier.idia.ac.za/viz-bin/VizieR-3?-source=I/360) ;
  https://vizier.nao.ac.jp/viz-bin/VizieR ; https://vizier.hia.nrc.ca/viz-bin/VizieR ; GAVO https://dc.g-vo.org/tap
- Outage reports: https://github.com/mwcraig/bandaid/issues/169 ; https://github.com/lgriffin/SDP/issues/107 ;
  https://github.com/m-samland/spherical/pull/262 ; https://github.com/muscat-team/muscatdb/issues/337 ;
  https://www.cloudynights.com/forums/topic/1014044-vizier-down/ ; CDS Facebook notice
  https://www.facebook.com/CDSportal/posts/pfbid02VYHUF2Sv76SshaR29psMYhuLCxYaoy1HoAL5UtPZBiDpDRsVmx65vMHRPBSWWLFil ;
  https://forums.aavso.org/t/vizier-outage-was-vsp-is-still-down/4729 ;
  https://stargazerslounge.com/topic/449777-is-simbad-database-france-offline/ ; CDS news
  https://cds.unistra.fr/news/ ; PHP CVE brief https://unit42.paloaltonetworks.com/cve-2026-109618-cve-2026-109619/
- Alternatives probed: MAST Pan-STARRS API https://catalogs.mast.stsci.edu/api/v0.1/panstarrs ; ATLAS-REFCAT2
  https://archive.stsci.edu/prepds/atlas-refcat2/
