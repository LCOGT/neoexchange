# apophis2 recovery analysis (Q18) — 2026-09-29

Read-only inventory over ssh of `apophis2` (CentOS 7.9, EOL; kernel 3.10.0-1160.49.1 from 2021; uptime 457 d; `/data` 37 TB, **96 % full**). Raw output: `inventory-2026-09-29.txt`, `inventory2-…`, `inventory3-…` (secrets redacted). Patches and files fetched: `uncommitted.patch`, `stashes/pipelines-stashes-0-4.patch`, `scripts/`, `home-cron-scripts/`.

## 1. What runs on apophis2 (three different code versions)

| Process | Checkout / branch | Interpreter & stack | DB | Started |
|---|---|---|---|---|
| dramatiq workers (`dramatiq-gevent --processes 4 --threads 1 --watch . django_dramatiq.setup django_dramatiq.tasks core.tasks`) | `~/git/neoexchange-devel`, `pipelines` @ `8d32e1c8` (= origin, pulled 2026-09-29) **+ uncommitted patch** | `~/venv/neocode39_psfphot_venv`: Python 3.9.13 (`/opt/lcogt-python39`, built against OpenSSL 1.0.2k), Django 3.1.14, numpy 1.23.5, **astropy 6.0.1**, photutils 1.11.0, dramatiq 1.14.2, django-dramatiq 0.11.0, pySLALIB 1.0.7, matplotlib 3.5.1 | `neoexchange-dev-copy` on `prod-shared1-pg14-writer-pgbouncer.lco.earth` (dev database on the shared prod PG14 cluster), `USE_S3=False` | by hand 2026-07-29 (`manage.py rundramatiq --reload --use-gevent …`); `--reload` means a `git pull` live-swaps worker code |
| `run_pipeline` (manual) | same | same | same | last seen 2026-07-31 (`--datadir /apophis/eng/rocks/20260731/164216_…`, Didymos COJ fields with `--refcat PS1 --dia`) |
| FLOYDS spectra download cron (`20 19,22,23 * * * source ~/download_FLOYDS_data_cron`) | `~/git/neoexchange`, **`issue-626_PDS_liens` @ `92490a15` (2024-08-08)**, last fetched 2024-08-08 | `~/venv/neoexchange-django31-venv`: **Python 3.6.5**, Django 3.1.7, astropy 3.2.3, numpy 1.19.2, photutils 0.7.1 | **prod `neoexchange`** DB, `USE_S3=True` (`~/cronwrapper_S3`) | cron |
| redis 3.2.12 | system service (`redis.service`, enabled) | — | — | boot |

Binaries: `sex` 2.19.5, `scamp` 2.0.4, `swarp` 2.38.0, `cdsclient` 3.83 (LCO el7 RPMs), `hotpants`, gnuastro tools, `convexinv` in `/usr/local/bin`; `fo`/`find_orb`/`astcheck`/`sat_id` in `~/bin`; **no `mtdlink`** despite the cronwrapper comment. `docker` CLI present.

Consequences for the plan: the pipeline workers have been validated against **astropy 6.0.1**, not 5.3.4 (the `<6.0` pin is already violated in production — supports §5.2); the FLOYDS cron is a *fourth* production code version (issue-626 @ Aug 2024 on Python 3.6) writing to the **prod** DB — it must move into the container (the image crontab already carries the same cron line → **Q19**: is the prod pod also running it?).

## 2. The uncommitted patch on `~/git/neoexchange-devel` (`uncommitted.patch`, 4 files, +90/−12)

| Change | Disposition |
|---|---|
| `core/management/commands/make_reference_fields.py`: with `--blocknum`, skip blocks that are not for the current field | **commit** (fix) |
| `photometrics/catalog_subs.py`: `funpack_fits_file(all_hdus=True)` handles raw MEFs whose extensions are all named `SCI` | **commit** (fix) |
| `catalog_subs.py`: `sort_rocks()` symlinks `e00` frames when no `e91` exists (raw-only data) | **commit** (feature); drop the `print(fits_filepath, …)` |
| `catalog_subs.py`: `logger.info("Updating FWHM to {new_fwhm:.4f} …")` lacks the `f` prefix (pre-existing bug) and a `print` was added beside it | fix the f-string, drop the print |
| `catalog_subs.py`: new `local_determine_original_name()` and `local_find_block_for_frame()` — verbatim copies of `core/views.py:3455 determine_original_name` and `:3628 find_block_for_frame` (copied to avoid the `views → catalog_subs` import cycle) | **refactor**: move the two helpers out of `core/views.py` into `photometrics/catalog_subs.py` (views already imports from it) and delete the `local_*` copies |
| `catalog_subs.py`: `update_frame_zeropoint(header, ast_cat_name, phot_cat_name, frame_filepath, frame_type)` — parameter renamed from `frame_filename`, now needs a full path (reads the header for Swope's non-unique `rccd*` filenames), filters the `Frame` by the found `Block`, and now also stores `frame.fwhm` | **load-bearing and inconsistent**: HEAD's `pipelines/processdata.py:511,523` already call `frame_filepath=` (so `origin/pipelines` alone raises `TypeError` in the zeropoint stage), while HEAD's `catalog_subs.py:2078,2081` and `tests/test_catalog_subs.py:3669,3684` still call `frame_filename=` (so the *patched* tree breaks those). Resolution: keep the new name, accept a bare filename too (skip the header lookup when no directory part), update the 4 remaining callers, add a Swope-case test |
| `catalog_subs.py`: `get_or_create_CatalogSources()` `flux_aper_index 3→4`, `aper_scaling 4→5`, default `aperture_radius_arcsec 3.0→1.0` | **decision (Q20)** — selects a different aperture from the multi-aperture list (index 4 = the odd 22.00 px entry) |
| `photometrics/configs/sextractor_neox_ldac.conf`: `DETECT_THRESH`/`ANALYSIS_THRESH` **3.0 → 1.2 σ**; `PHOT_APERTURES` 10 → 12 px (commented alternatives: 1″–10″ radius list for Sinistro, "10,000 km aperture for 3I") | **decision (Q20)** — experiment tuning (3I/ATLAS, Didymos) vs default; changes every catalogue and several test expectations |
| `photometrics/external_codes.py`: `print("Scamp cmdline=", …)` | drop or `logger.debug` |

## 3. Stashes on `~/git/neoexchange-devel` (14)

- `stash@{0..3}` (pipelines, successive snapshots of the same work above; also `sextractor_neox_ldac_multiaper.conf` edits — DEBLEND_MINCONT 0.005, PIXEL_SCALE 0, aperture lists) → **superseded**: the conf edits are already in HEAD, the code is in the working tree. Drop after the patch is committed.
- `stash@{4}` (settings.py: `django_dramatiq` position, `AdminMiddleware`, `DRAMATIQ_RESULT_BACKEND`) → already in HEAD; drop.
- `stash@{5..13}` (2018–2021: focus_project_support, staticsource_photometry, GPS_satellites (`backfill_blocks.py` +96/−91), gaia-dr2 era, migrate-to-3.6, feature/astrometry) → archaeology; optionally export with `git stash show -p` into `docs/migration/apophis2/stashes/` and drop.
- Local branch `fix_fits_oserror` (7ffb4f82, 2020) is already contained in main's lineage — nothing marooned there.

## 4. Other checkouts

- `~/git/neoexchange` (issue-626 @ 2024-08-08, runs the FLOYDS cron): two small uncommitted fixes — `lightcurve_extraction.py` (ignore FWHM ≤ 0 in the conditions plot), `gf_movie.py` (zero offsets when the target is off-frame; drop its `print`) → **commit** to issue-626/main. 13 stashes (issue-626 WMSCLOUD/PDS-example WIP at {0},{1}; the rest 2017–2021).
- `~/git/neoexchange-stacking` (= origin/stacking tip): untracked `pipelines/mpi.py` (1.8 KB, 2024-03) and `pipelines/constants.py` → fetched to `scripts/stacking/`; **commit to `stacking`** or drop.
- `~/git/neoexchange-multiaper` (2023): two modified analysis scripts + 2 stashes → archive.

## 5. Orphan files in `~/git/neoexchange-devel/neoexchange` (fetched to `scripts/`)

`DART_stuff_20230429.py`, `dart_mro_20230915/18/21/29.py`, `gps_sats_blocks.py` are IPython session transcripts (`get_ipython().system(...)`) from the DART/MRO and GPS work — not production code; keep them with the other reduction notes (e.g. under `docs/DART_2023/`) or drop. `direct_blocks`, `Bad_frame`, `Log_tests_1`, `moon_phases_*.tsv`, `dump.rdb` (a redis dump written into the repo dir), two PNGs → drop.

## 6. Recommended order (Phase 0, step 0)

1. Stop the dramatiq workers before touching the checkout (`--reload` live-swaps code), or do the work on a branch pushed from the workstation and only `git pull` on apophis2 when ready.
2. On a `prep/apophis2-recovery` branch from `pipelines`: apply `uncommitted.patch` minus the debug prints; do the `update_frame_zeropoint` reconciliation and the helper move; run `photometrics` + `pipelines`-related tests.
3. Decide Q20; if the tuning values are experiment-specific, keep the repo defaults and move the 1.2 σ / 12 px / index-4 settings into a documented alternative config (or CLI options).
4. Commit the issue-626 checkout fixes and the stacking files to their branches.
5. Drop stashes 0–4 (after 2 is merged); export/drop 5–13.
6. Only then run the pipelines baseline again — it is the true "before" state for the merge.
