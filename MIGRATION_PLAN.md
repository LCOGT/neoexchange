# NEOexchange migration plan: merge `pipelines` into `main`, Python 3.11, dependency refresh

*Draft for review, prepared 2026-09-28/29 from an analysis session against `origin/main@0babdc61` (3.17.1, 2026-08-28) and `pipelines@8d32e1c8` (3.14.6b, 2026-09-21). Evidence, test lists and the scripts used are in `docs/migration/`. Nothing described here has been applied to any branch.*

## 0. Summary

1. **`origin/main` already made the platform move.** Release 3.17.0 (commit `1d7daf8f`, 2025-12-19) put main on Rocky 9 + Python 3.11 + Django 4.2 + numpy 1.26.4 + astropy 5.3.4 + pyslalib 1.0.10. (The local `main` checkout was 89 commits behind and still looked like Python 3.9.)
2. **Merging `origin/main` into the pipelines code is therefore most of the Python migration.** What remains is pipelines-specific: its pins (Django 3.1, DRF 3.12.1, dramatiq/redis/watchdog, numpy 1.23.5, photutils 1.11.0, calviacat/mastcasjobs), the Rocky 9 image (main's image dropped `sextractor`/`scamp`/`mtdlink`/`cdsclient`, which the pipelines need), and the redis/dramatiq runtime that production does not have.
3. **Interpreter risk is low and was measured:** the unchanged pipelines `requirements.txt` installs under `/usr/bin/python3.11`, and the suite fails on exactly the same 115 tests on 3.9 and 3.11.
4. **The real risks:** (a) the pipelines suite is already red in its own environment and one test module does not import; (b) six files carry ~80% of the merge-conflict volume and need semantic resolution; (c) Rocky 9 has no packaged `scamp`/`swarp`/`cdsclient`/`hotpants`/`mtdlink`; (d) the pipeline runtime (redis, `rundramatiq`, `run_pipeline`) lives on apophis2, a CentOS 7.9 host that is EOL and cannot follow the ecosystem to Python 3.11; (e) **code running on apophis2 has never been committed to `pipelines`** — the merge must be resolved against what actually runs, so that code has to be inventoried and committed first (Phase 0, step 0; Q18).
5. **Recommendation:** one integration branch off `origin/main`; merge `pipelines` into it once (no rebase, no chunking); "main wins" for shared code with pipelines' additions layered on; gate on the unit suite run *inside the built image*; rehearse the DB migration in the `dev` namespace on a fresh prod snapshot; containerise the pipeline runtime. Then Django 5.2 LTS (small) and astropy 7 (small) as separate PRs.

Effort (one person): prep ½–1 d · merge + resolution 2–4 d · dependencies 1 d · container/binaries 2–3 d (+ LCO ops dependency) · verification/release 1–2 d ⇒ **~1.5–2.5 weeks elapsed**. Follow-ons: Django 5.2 **1–2 d**; astropy 7 **~1 d + a golden-output regression**.

## 0.1 Status and how to resume

*Last updated 2026-09-29.* Analysis complete; plan under review; **no branch has been modified and nothing has been committed** (this file and `docs/migration/` are untracked). Resume notes also live in the Serena project memories `migration-pipelines-to-main` and `neoexchange-environments-and-hosts` (`.serena/memories/`), and `CLAUDE.md` points here.

- Answered so far: Q1–Q4, Q15, Q16 (§4). Open: Q5–Q14, Q17, **Q18**.
- Before Phase 1 can start honestly: (1) commit the recovered apophis2 code (Phase 0 step 0; inventory done, patch saved, decisions Q20 pending); (2) decisions Q6 (`issue-626` sequencing), Q7 (18 pipelines-only failing tests), Q8 (`backfill_blocks.py`), Q19 (FLOYDS cron).
- Scratch state from the analysis session — detached worktrees `wt-merge` (trial merge left in progress), `wt-main`, `wt-pipelines`; venvs `venv311_asis`, `venv311_astropy7`; full test logs — lived under `/tmp/claude-*/scratchpad` and may be gone. `git worktree prune` removes stale entries. Recreate the trial merge with `git worktree add --detach <dir> origin/main && git -C <dir> merge --no-commit --no-ff pipelines`.
- Re-review checklist (numbers in §1 are from 2026-09-28 and drift as `origin/main` moves): `git fetch && git rev-list --left-right --count origin/main...pipelines`; `git merge-tree --write-tree origin/main pipelines | grep ^CONFLICT`; re-run `docs/migration/tools/run_tests_nonet_warn.sh` on both branches (network off, ~6 min each) and compare with `docs/migration/failing-tests-*.txt`.
- Status log: 2026-09-28 analysis and measurements · 2026-09-29 plan written to disk; apophis2 uncommitted code reported (Q18) · 2026-09-29 apophis2 inventoried read-only over ssh (Q18 findings, Q17 tentatively PG14, new Q19/Q20); recovery patch and scripts saved under `docs/migration/apophis2/`. · 2026-09-29 Q20 answered (defaults likely; Tim owns the conf commit); recovery-branch design agreed, execution deferred ("not yet").

## 1. Verified current state

### 1.1 Branches

| | `origin/main` (0babdc61) | `pipelines` (8d32e1c8) |
|---|---|---|
| Version | 3.17.1 | 3.14.6b |
| Base image / Python | Rocky 9 / `python3.11` | Rocky 8 / `python39` |
| Django / DRF | 4.2.x / – | 3.1.14 / 3.12.1 |
| numpy / astropy / photutils | 1.26.4 / <6.0 / unpinned | 1.23.5 / <6.0 / ==1.11.0 |
| Extra stack | django-cors-headers, tenacity | dramatiq, django-dramatiq 0.11.0, redis 3.5.3, watchdog<4, calviacat, mastcasjobs, `requirements-trippy.txt` |
| Merge-base | `8386bcda`, **2 Aug 2022** | |
| Commits / files since base | 493 / 165 | 506 / 182 (55 files touched on both sides) |

### 1.2 Trial merge (`docs/migration/conflicts.md`)

`git merge --no-commit --no-ff pipelines` on a detached worktree of `origin/main`: **32 conflicting files, 124 hunks, ~10.6k lines inside markers**; 97 files auto-added, 31 auto-modified, 7 deleted; one modify/delete (`core/management/commands/download_archive_data.py` — deleted on pipelines in 2021, still used by main's FLOYDS cron → keep main's); one add/add (`photometrics/lightcurve_subs.py`).

| File | hunks | conflict lines | nature |
|---|---:|---:|---|
| `photometrics/tests/test_pds_subs.py` | 8 | 5794 | the same 12 test classes added on both sides at different positions |
| `photometrics/tests/test_external_codes.py` | 4 | 994 | pipelines adds ~870 lines of tests |
| `core/tests/test_views.py` | 5 | 810 | pipelines adds 675 lines of tests |
| `photometrics/tests/test_catalog_subs.py` | 18 | 659 | mostly pipelines-only additions |
| `photometrics/pds_subs.py` | 13 | 599 | main-side additions vs pipelines Swope/MRO support |
| `core/views.py` | 6 | 572 | pipelines adds 529 lines; `run_sextractor_make_catalog` on both sides |
| `photometrics/external_codes.py` | 9 | 261 | `run_sextractor`, `convert_file_to_crlf` on both sides |
| `core/tests/test_models.py` | 3 | 255 | |
| remaining 24 files | ≤6 each | ≤130 each | mechanical (ELP MPC codes `V45/V47` vs temporary `V98/V99`, imports, docstrings, `Dockerfile`, `requirements.txt`, `settings.py` ×2 tiny hunks, `urls.py`, `README.md`) |

### 1.3 Test baselines (`docs/migration/test-baselines.md`)

- **pipelines @ Python 3.9:** 1761 ran, **73 failures + 50 errors** (115 distinct), 17 skipped. `astrometrics/tests/test_ephem_subs.py:23` lacks the `SimpleTestCase` import (since `c2b43b92`, Jan 2026) so the module fails to import and **~229 ephemeris tests have not run on the branch for nine months**. Identical result under Python 3.11 with the same pins.
- **origin/main @ Python 3.11:** 1908 ran, 3 failures + 23 errors: 21 network (`vizier.cfa.harvard.edu` 504/timeouts), 3 binary-version (`TestSCAMPRunner` 29≠30, two `TestCheckCatalogAndRefitNew`), 2 caused by matplotlib 3.10 in that venv (astropy 5.3.4's WCSAxes imports `AnchoredEllipse`, removed in 3.10). Effectively green.
- ≈96 of the 115 pipelines failures exist on main and pass there (ADES/PSV output, ELP codes, semester dates, `FieldDoesNotExist` NameError, astropy-5 `Quantity.__round__`…) → "main wins". **18 fail only on pipelines** (`docs/migration/failing-tests-pipelines-only.txt`): `TestReadReferenceFrameHeader` (needs the untracked 18 MB `reference_test_frame.fits`), `TestSkysclim`, `TestRunAstarithmetic` ×3, `TestRunAststatistics`, `TestPerformAperPhotometry` ×4, `TestFrameAperturePhotometry` ×4, `TestSwarpRunner`/`TestSwarpAlignRunner` (swarp-version diffs), `TestUpdateFITSWCS.test_update_FITS_WCS_newer_SCAMP`, `TestWritePDSLabel.test_write`. 16 fail on both branches (environment).
- **33 tests need the network** (`docs/migration/network-dependent-tests.txt`); with the network disabled the whole suite runs in ~6 min.

### 1.4 Dependency facts (PyPI metadata + install/import experiments)

- **DRF 3.12.1 is broken on Django 4.2** (`ImportError: cannot import name 'parse_header' from django.http.multipartparser`, reproduced). 3.15.2+ require Django ≥4.2; 3.16.x covers 4.2–5.2; 3.18.x requires ≥5.2.
- `django-dramatiq` 0.11.0 imports and configures under Django 4.2 + dramatiq 2.1.0; 0.12+ require Django ≥4.2 (latest 0.15.0, py ≥3.10). dramatiq 1.17.1 fixed the watchdog-4 breakage behind the `watchdog<4.0` pin; 1.18 needs py ≥3.9; 2.x needs py ≥3.10 and redis ≥4.
- `pyslalib` 1.0.10 builds with **meson-python** (no `numpy.distutils`); the "install numpy first" Dockerfile magic dates from 1.0.7. Also clears the way to Python 3.12.
- `matplotlib<3.5.2` (June 2022, no recorded reason): 3.5.1 has no cp311 wheel → source build. astropy 5.3.4 itself only excludes exactly 3.5.2, but its WCSAxes needs `AnchoredEllipse` (present ≤3.8, deprecated 3.9, removed 3.10). Under astropy 5.3.4 the workable window is **`>=3.7,<3.9`** (cp311 + cp312 wheels); astropy 7 removes the ceiling.
- bokeh 2.3.0 / Jinja2 2.11.3 / MarkupSafe 1.1.1 work on 3.11 (production 3.17.x runs them); bokeh 2.3.0 uses no `distutils`/`pkg_resources`. Dependabot PR #669 (bokeh 3.8.2) is CONFLICTING and would break `core/plots.py` wholesale (31 uses of `plot_width`/`Panel`/`circle`…); bokeh 2.4.3 accepts Jinja2 3 and would let the Jinja2/MarkupSafe pins go.
- photutils on pipelines is only `photutils.aperture` + `photutils.centroids`; 1.11.0 works with numpy 1.26.4; 2.3.0 needs numpy ≥1.25/astropy ≥5.3/py ≥3.11; 3.0 needs numpy ≥2. main has no photutils imports at all, yet its image carries photutils 2.3.0 — **main's `requirements.txt` ≠ what its working image/venv contain**.
- `nose` is required by both but imported nowhere (and broken on py ≥3.10); `fits2image` was removed on main (PR #673) and is unused on pipelines.
- Python 3.9 reached EOL Oct 2025; 3.11 EOL Oct 2027. Django 4.2's extended support ended April 2026 (no security fixes now); Django 5.2 LTS is supported to April 2028 and needs Python ≥3.10 and **PostgreSQL ≥14**.

### 1.5 Migrations

- Both branches: `makemigrations --check` clean. Disjoint chains after 0064 — main: `0065_blockobserver → 0067_merge → 0068_alter_proposal_code → 0069_alter_block_site`; pipelines: `0065_asyncprocess_pipelineprocess → 0066 → 0067 (Frame.color/color_err/color_used/zeropoint_src) → 0068_merge → 0069 (SourceMeasurement.aperture_size/snr) → 0070 → 0071_merge → 0072 → 0073 (Block.site/telclass choices, SuperBlock.tracking_number index) → 0074`. `0065_auto_20221012_1840` and `0066_exportedblock` are byte-identical on both.
- After the merge: `0075_merge_…` is mandatory; both sides altered `Block.site` choices so expect choices-only `AlterField`s too (no DDL on Postgres). All pipelines-side schema changes are additive/nullable → the migrated DB stays usable by the previous image (rollback-safe).
- **Production DB (prod namespace) has only main's chain; the pipelines chain was only ever applied to the separate dev DB (a 2022 snapshot).** Migrations are applied by the helm chart at deploy.

### 1.6 Container and binaries (`docs/migration/rocky9-package-availability.txt`)

- `rockylinux:9` + EPEL 9 provides `sextractor 2.28.2`, `plplot 5.15`, `gnuastro 0.24` (astwarp/astnoisechisel/astconvertt/aststatistics/astcrop), `cfitsio`, `dos2unix`. **Not available for el9 anywhere: `scamp`, `swarp`, `cdsclient`, `hotpants`, `mtdlink`** (EPEL 9 has none; Fedora dist-git has scamp/swarp/cdsclient only in rawhide; LCO's `repos/lcogt/9` has none). LCO's `repos/lcogt/src/` holds SRPMs for `mtdlink-1.0.2`, `scamp-2.0.4`, `cdsclient-3.83`, `hotpants-6d85a93`, `sextractor-2.19.5` → rebuildable for el9.
- The pipelines call (`external_codes.find_binary`): `sex`, `scamp`, `swarp`, `hotpants`, `mtdlink`, `fo`, `period_scan`, `unix2dos`, plus the gnuastro tools.
- Inside a Rocky 9 image with `python3.11` installed, `python3` is **3.9.18**; main's crontab and cron scripts already say `python3.11` (pipelines' still say `python3`; auto-merges to main's).
- The locally built `docker.lco.global/neoexchange:test_new_pyslalib` (3.17.0a, Dec 2025) confirms the production image shape: Rocky 9.3, py3.11, Django 4.2.27, numpy 1.26.4, photutils 2.3.0, matplotlib 3.5.1 (source-built), pyslalib 1.0.10, `fo` present, **no** sex/scamp/swarp/hotpants/mtdlink/unix2dos. Today's production image cannot run the reduction pipelines.

### 1.7 Production topology (from Q&A)

- Web app + crons: EKS `prod` namespace, prod database; migrations run by the helm chart on deploy.
- `pipelines` branch: EKS `dev` namespace, separate dev database (2022 snapshot).
- Pipeline runtime: **apophis2 (CentOS 7.9, EOL June 2024; kernel from 2021; 457 d uptime; `/data` 96 % full)** — redis 3.2.12 system service; dramatiq workers started by hand on 2026-07-29 with `--reload` from `~/venv/neocode39_psfphot_venv` (Python 3.9.13 built against OpenSSL 1.0.2k; **astropy 6.0.1**, Django 3.1.14, numpy 1.23.5, photutils 1.11.0) against the **dev** DB `neoexchange-dev-copy` on the shared prod PG14 cluster; `run_pipeline` run by hand (last 2026-07-31). Binaries are the el7 LCO RPMs (scamp 2.0.4, sextractor 2.19.5, swarp 2.38.0, cdsclient 3.83) plus source-built hotpants/gnuastro/convexinv; **no mtdlink**. A separate checkout (`~/git/neoexchange`, issue-626 @ 2024-08-08) runs the FLOYDS spectra cron under Python 3.6.5/Django 3.1.7 against the **prod** DB (Q19). Full detail: `docs/migration/apophis2/ANALYSIS.md`.
- glibc 2.17 on CentOS 7 is being abandoned by the wheel ecosystem (`docs/migration/python311-wheel-glibc-check.txt`): pillow 12, gevent 26, greenlet 3.5, scikit-image 0.26, torch 2.14 ship only `manylinux_2_28` wheels. Python ≥3.10 also needs OpenSSL ≥1.1.1 (CentOS 7 has 1.0.2). A 3.11 venv on apophis2 is a dead end.

### 1.8 Other branches and working-tree hygiene

- `stacking` is pipelines-derived (+151 commits, Jun 2026) → re-merge after this lands. `issue-626_PDS_liens` is main-derived (+64, Apr 2026) and rewrites `pds_subs.py`/`test_pds_subs.py`/`external_codes.py` and adds `image_subs.py` (pipelines has its own `image_subs.py`, ~480 lines different). Small main-derived branches: `issue-665` (+4), `add-jpl-orbit-fallback` (+4), `notebook/comet-discovery-distance` (+3), `feature/bar_visibility_plot` (+2), `issue-656_FLOYDS_BANZAI_support` (+12).
- Uncommitted in the devel checkout: `core/management/commands/backfill_blocks.py:147` changes `blocks.count() == 0` to `== -1` (debugging leftover?); a comment in `pds_subs.py`; Hera notebooks; untracked `photometrics/tests/reference_test_frame.fits` (18 MB, needed by `test_catalog_subs.py:5054`, which only reads the header), `wtf.png`, `yeehaw.png`, `summarize_*.py`, `update_A11pl3Z.py`, `new_scamp.cfg`.

## 2. Plan

**Direction:** `git checkout -b integrate/pipelines-into-main origin/main && git merge --no-ff pipelines` (ours = main, matching the policy below). Not a rebase (506 pushed commits), not a squash (six years of history), not chunked (six files dominate). Set `merge.conflictstyle=zdiff3` and `rerere.enabled=true`.

### Phase 0 — Preparation (½–1 day, plus the apophis2 recovery)

0. **Recover the code marooned on apophis2 (Q18) — inventoried 2026-09-29, see `docs/migration/apophis2/ANALYSIS.md`.** Remaining actions, in order: (a) stop the dramatiq workers first (they run with `--reload`, so a `git pull` live-swaps their code) or prepare everything on a branch from the workstation; (b) on `prep/apophis2-recovery` from `pipelines`, apply `docs/migration/apophis2/uncommitted.patch` minus its debug prints, reconcile `update_frame_zeropoint` (new `frame_filepath` name, accept bare filenames, update `catalog_subs.py:2078,2081` and the two tests, add a Swope case) and move `determine_original_name`/`find_block_for_frame` from `core/views.py` into `photometrics/catalog_subs.py` instead of the `local_*` copies; (c) decide **Q20** for the sextractor thresholds/apertures and the aperture index — keep experiment values out of the defaults unless intended; (d) commit the two fixes from the `~/git/neoexchange` checkout to issue-626/main and `pipelines/mpi.py`+`constants.py` to `stacking`; (e) archive or drop the IPython transcripts and scratch files; drop stashes 0–4, export/drop 5–13; (f) re-run the pipelines baseline — only then is §1.3 the true "before" state.

   **Agreed design for (b) — not started (2026-09-29, "not yet"):** on `prep/apophis2-recovery` off `pipelines`, as four separable changes: (1) *refactor* — move `determine_original_name` and `find_block_for_frame` from `core/views.py:3455/3628` into `photometrics/catalog_subs.py` (cycle-free: views already imports from catalog_subs, catalog_subs imports nothing from views); `core/views.py` re-imports them so `pipelines/processdata.py:20` and the four `TestCheckCatalogAndRefitNew.test_find_block_for_frame_*` tests keep working; delete the `local_*` copies. (2) *`update_frame_zeropoint` reconciliation* — adopt the apophis2 signature (`frame_filepath`, Block-scoped Frame lookup, store `fwhm`), tolerate bare filenames, switch `catalog_subs.py:2078,2081` and `test_catalog_subs.py:3669,3684` to the new keyword, add a Swope `rccd*` test. (3) *fixes* — `make_reference_fields --blocknum` guard, `funpack_fits_file` raw-MEF, `sort_rocks` e00 symlink, un-f-stringed `logger.info`; drop the three debug prints. (4) *tuning (code half of Q20)* — `get_or_create_CatalogSources` aperture index/scaling/default as its own commit; `sextractor_neox_ldac.conf` is Tim's to diff/review/commit. Verify with ruff + `photometrics.tests.test_catalog_subs` + `core.tests.test_views.TestCheckCatalogAndRefitNew`.
1. Refresh local `main` to `origin/main`. Decide `issue-626_PDS_liens` sequencing (before is recommended if it is near-ready); land the small ready main-side branches first.
2. Clean the pipelines tree on a `prep/pipelines-cleanup` branch: revert/commit the `backfill_blocks.py` change; commit the `pds_subs.py` comment; replace the 18 MB fixture with a header-only FITS (`fits.PrimaryHDU(header=hdr).writeto(...)`) and commit it; move stray scripts/PNGs out or gitignore; **restore `SimpleTestCase` in `test_ephem_subs.py`** and re-run the suite so the branch baseline is honest; push.
3. Triage the 18 pipelines-only failing tests (fix, or skip with a reason). Do not spend time on the ≈96 shared ones.
4. Snapshot production facts: deployed image tag/branch, `SELECT name FROM django_migrations WHERE app='core' AND name >= '0065' ORDER BY id;`, PostgreSQL server version.

### Phase 1 — Integration merge (2–4 days)

| Area | Rule |
|---|---|
| Shared behaviour changed on both sides (ELP `V45/V47`, ADES/PSV output, semester dates, Django-4 idioms, astropy-5 fixes, `set_auto_axislabel` try/except, `unpack_sci_extension`) | **main wins**, then re-apply pipelines' *additions* (H01/MRO and I33/SOAR sites, `NONLCO_SITES`, `Frame.NEOX_SUB_FRAMETYPE = 93`, MRO archive paths, `funpack_fits_file(all_hdus=…)` as an extension of main's function, `NEOX_SUB_FRAMETYPE` in `lightcurve_subs`) |
| Pipelines-only code (`pipelines/` app, `core/tasks.py`, `run_pipeline`, hotpants/swarp/gnuastro runners, PDS Swope/MRO support, `image_subs.py`, admin registrations) | keep |
| `Dockerfile` | main's Rocky 9 file + pipelines' `git` + binaries (Phase 3) |
| `requirements.txt` | merged per §2 Phase 2 |
| `settings.py` | main's (`STORAGES`, `DEFAULT_AUTO_FIELD`, CORS) + pipelines' `django_dramatiq`/`rest_framework`/`pipelines` apps, `PIPELINES`, `DRAMATIQ_*`, logging block; `VERSION = '3.18.0'` |
| `urls.py` | main's `path()` version + `path('pipelines/', include('pipelines.urls'))`; `auth_backend.py`/`dashboard.py` `ugettext` were fixed on main and are untouched on pipelines → auto-merge |
| `download_archive_data.py` | keep main's |
| Big test files | resolve **class-by-class**: main's class where both define it unless the pipelines copy has extra Swope/MRO cases (then union); dedupe `run_sextractor`, `convert_file_to_crlf` (`external_codes.py`) and `run_sextractor_make_catalog` (`views.py`) |
| `neox/tests/base.py` | main's (`from numpy import ndarray, long` fails on numpy ≥1.24; main fixed it in `ffe2c474`) |
| `README.md` | concatenate histories under a 3.18.0 heading |

Then `ruff check --select F,E9`, `manage.py check`, `manage.py makemigrations` (expect `0075_merge_*` + choices-only `AlterField`s), commit.

Verification A: fresh Python 3.11 venv from the merged `requirements.txt`; run `core astrometrics photometrics` with the network disabled (`docs/migration/tools/run_tests_nonet_warn.sh`); target = main's no-network baseline (37 → the 33 network tests + binary-version ones) with every residual failure classified. Verification B (only if A shows unexplained failures): same tree in a Python 3.9 venv (`neocode39-astropy53_venv` is nearly that environment) to separate merge effects from interpreter/deps. Verification C: `neox/tests` Selenium run.

### Phase 2 — Dependencies (1 day)

| Package | pipelines | origin/main | Merge target | Reason |
|---|---|---|---|---|
| Python | 3.9 | 3.11 | **3.11** | identical test results 3.9 vs 3.11 |
| numpy | ==1.23.5 | ==1.26.4 | **==1.26.4** | no removed aliases left except `neox/tests/base.py` (main's fix) |
| Django | 3.1.x | >=4.2.20,<5.0 | **>=4.2.30,<5.0** | 5.2 as the next PR (§5.1) |
| djangorestframework | ==3.12.1 | – | **>=3.16,<3.17** | 3.12.1 ImportError on 4.2 |
| django-dramatiq | ==0.11.0 | – | **>=0.13,<0.16** (verify `rundramatiq`, admin) | 0.12+ require Django ≥4.2 |
| dramatiq | (1.16) | – | **`dramatiq[redis,watch]>=1.17.1,<2`** | 1.17.1 fixes watchdog-4; 2.x later |
| watchdog | <4.0 | – | **drop** | superseded |
| redis | ==3.5.3 | – | **>=4,<6** | 2020 pin, no reason |
| astropy | <6.0 | <6.0 | keep `<6.0` (5.3.4) for the merge | 7.x in Phase 2b |
| photutils | ==1.11.0 | unpinned | **==1.11.0** for the merge | 2.3 in Phase 2b |
| matplotlib | <3.5.2 | <3.5.2 | **>=3.7,<3.9** | no cp311 wheel for 3.5.1; astropy 5.3 WCSAxes needs `AnchoredEllipse` (<3.10) |
| bokeh / Jinja2 / MarkupSafe | 2.3.0 / <3.0 / <2.0 | same | **keep** | works; 2.4.3 later |
| pyslalib | unpinned | `pySLALIB` | **>=1.0.10** | meson build |
| gunicorn[gevent] | ~=20.1 | ~=23.0 | main's | |
| calviacat / mastcasjobs | git `@main`/`@master` | – | pin to **commit SHAs**; decide fork (Q9) | moving targets |
| nose, fits2image | present | nose | **drop** | unused |
| django-cors-headers, tenacity | – | present | keep | |
| requirements-trippy.txt | present | – | **local only**, not in the image (decided) | torch is glibc-2.28-only anyway |

Also: regenerate a lock (`pip freeze` → `requirements.lock`, or `uv pip compile`) and install the image from it so "tested" and "deployed" stop diverging; `pyproject.toml` ruff `target-version = "py311"`.

**Phase 2b — astropy refresh (separate PR, ~1 day + golden-output regression; see §5.2):** `astropy>=7.2,<8`, `photutils>=2.3,<3`, `aplpy>=2.2.1`, `matplotlib>=3.8,<3.11` (3.8.4 tested; 3.9/3.10 to verify), numpy stays 1.26.4; fix `photometrics/SA_scatter.py:79` and `tests/test_SA_scatter.py:56` (`transform_to(coordinates.ICRS())`).

### Phase 3 — Container and runtime (2–3 days + ops dependency)

**3a. Image.** Rocky 9 (main) + `git` (pip git+ deps) + EPEL `sextractor plplot gnuastro dos2unix cfitsio` + builder stage(s) for `scamp`, `swarp`, `cdsclient`, `hotpants`, `mtdlink` from the LCO SRPMs or upstream — or LCO packaging publishes el9 RPMs (better long-term). Pin binary versions and align test expectations to them. `node` stays (bokeh custom TypeScript models). No trippy/torch.

**3b. Pipeline runtime — containerise; do not build a 3.11 venv on apophis2.** One image for web (EKS `prod`), supercronic crons, the dramatiq worker and the `run_pipeline` CLI:

| Option | How | When |
|---|---|---|
| **A. Worker + redis in EKS** (cleanest) | redis in-cluster or ElastiCache; `rundramatiq` Deployment in `prod` with `REDIS_HOSTNAME`; same image tag as the web pods; same `/data/eng/rocks` mount `docker/init` already assumes; helm-chart change | if EKS pods can reach the pipeline data (S3 via `USE_S3`, or the NFS behind `/data/eng/rocks`) — **Q14** |
| **B. Container host on-prem** (data locality) | replace apophis2 with a Rocky 9 host; podman/docker; systemd/Quadlet units for redis + worker (`Restart=always`, journald); `run_pipeline` via `podman run --rm -v /data/eng/rocks:/data/eng/rocks <image> python3.11 manage.py run_pipeline …` behind a wrapper | if data must stay on-prem; apophis2 itself only as a stopgap |
| C. Bare venv on a Rocky 9 host | what this workstation does | transitional only — two build recipes |

Until a broker exists, the merged web app still works: `core/tasks.py` `send_task` catches `RedisError` and marks the process failed. Confirm `manage.py check`/startup with no redis reachable.

**Acceptance gate:** run the unit suite **inside the built image** (`docker run --rm <image> python3.11 manage.py test core astrometrics photometrics`) so binaries/versions match production. Jenkins (`dockerPipeline`) only builds today; add this as a stage or a GitHub Action.

### Phase 4 — Release (1–2 days)

- Refresh the dev DB from a **fresh prod snapshot**, deploy the merged image to `dev`, let the chart run `migrate` → dress rehearsal of the prod migration (`0065_asyncprocess…0074` + `0075_merge`) on real data; click through the pipelines UI.
- Tag 3.18.0; deploy to `prod`; smoke: schedule/submit flow, target + block pages (bokeh), MPC/ADES downloads, crons, pipelines pages. Rollback = previous chart revision (migrations are additive).
- Fast-forward `pipelines` to `main` (or delete it); re-merge `stacking`; land `issue-626` if not already.

## 3. Verification gates (in order)

1. Pipelines baseline re-run after Phase 0 (with `test_ephem_subs` importing again).
2. Merged tree: `ruff --select F,E9`, `manage.py check`, `makemigrations` review.
3. Merged tree, Python 3.11 venv, network off: failing set ⊆ {33 network tests, binary-version tests}, each residual explained.
4. Selenium `neox/tests`.
5. Suite inside the built image.
6. Dev-namespace deploy on a prod snapshot + migrate + UI smoke.
7. Prod deploy + smoke; rollback path confirmed.
8. For Phase 2b (astropy 7): repeat 3 and a golden-output regression (same night of data through `run_pipeline` + PDS/ALCDEF/MPC/ADES exports under 5.3.4 and 7.2; `diff`).

## 4. Decisions and open questions

| # | Question | Status |
|---|---|---|
| Q1 | What runs in production? | **Answered:** prod namespace + prod DB = main; dev namespace + dev DB (2022 snapshot) = pipelines |
| Q2 | Pipelines migrations ever applied to prod DB? | **Answered:** no |
| Q3 | How is `migrate` run in prod? | **Answered:** helm chart on deploy |
| Q4 | Redis / worker today? | **Answered:** apophis2 (CentOS 7.9), manual `rundramatiq`, manual `run_pipeline` |
| Q5 | Binaries route (LCO el9 RPM rebuild vs Docker builder stages); canonical versions (workstation scamp 2.13.1/sextractor 2.28.2/swarp 2.41.5 vs old 2.0.4/2.19.5); mtdlink source | open |
| Q6 | `issue-626_PDS_liens` before or after the big merge | open (recommend before, if near-ready) |
| Q7 | Must the 18 pipelines-only failing tests be green pre-merge? | open |
| Q8 | Revert `backfill_blocks.py` `== -1`? | open |
| Q9 | Canonical `calviacat` (mkelley main vs talister fork SHA) | open |
| Q10 | Tag/mock the 33 network tests | open (recommended; list in `docs/migration/network-dependent-tests.txt`) |
| Q11 | Django 5.2 timing | open (recommend the PR right after the merge is deployed) |
| Q12 | Jenkins test stage / staging namespace | open |
| Q13 | RHEL 9 app-stream lifecycle for `python3.11` vs `python3.12` | open (informational) |
| Q14 | Where `/data/eng/rocks` lives; can EKS pods reach it? (decides 3b option A vs B) | open |
| Q15 | Python on apophis2 | **Answered:** 3.9 venv |
| Q16 | trippy/torch in the image? | **Answered:** no |
| Q17 | **PostgreSQL server version in prod** (Django 5.2 needs ≥14) | **Tentatively answered:** DB host is `prod-shared1-pg14-writer-pgbouncer.lco.earth` → PostgreSQL 14; confirm with `SELECT version()`. pgbouncer fronts it (no `DISABLE_SERVER_SIDE_CURSORS` set; works today) |
| Q18 | **Code marooned on apophis2** | **Inventoried 2026-09-29** (`docs/migration/apophis2/ANALYSIS.md`): a 4-file uncommitted patch on `~/git/neoexchange-devel` that is *load-bearing* (HEAD's `pipelines/processdata.py:511,523` already call the patched `update_frame_zeropoint(frame_filepath=…)`, so `origin/pipelines` alone is broken in the zeropoint stage), two small fixes on the `~/git/neoexchange` (issue-626) checkout, `pipelines/mpi.py`+`constants.py` on the stacking checkout, IPython transcripts, 14 stashes (0–4 superseded, 5–13 archaeology). Dispositions in ANALYSIS.md; Q20 pending — still **blocks Phase 1** until committed |
| Q19 | Does the prod pod's supercronic also run `download_FLOYDS_data_cron` (it is in the image crontab)? apophis2 runs it too — from `~/git/neoexchange` (issue-626 @ 2024-08) under **Python 3.6.5 / Django 3.1.7 / astropy 3.2.3** against the **prod** DB with `USE_S3=True` | open — duplicate or sole instance? Either way it belongs in the container |
| Q20 | Science-tuning changes in the apophis2 patch (`sextractor_neox_ldac.conf` thresholds/apertures; `get_or_create_CatalogSources` aperture index/scaling/default) | **Answered 2026-09-29:** they will probably become the defaults; **Tim diffs, reviews and commits `sextractor_neox_ldac.conf` himself**. The `local_*` helper copies must go — proper refactor of the import cycle (they were an emergency workaround before DART) |

## 5. Follow-on upgrades, sized

### 5.1 Django 4.2 → 5.2 LTS — small (1–2 days), do as its own PR after the merge is deployed

Evidence: main's whole suite under 4.2 with warnings forced on emits **one** `RemovedInDjango5xWarning` (`USE_L10N`). Static scan of both branches finds no `assertQuerysetEqual`, `index_together`, `length_is`, `get_storage_class`, CI fields, `make_random_password`, pytz or `timezone.utc`. Work items:

1. Delete `USE_L10N` (`neox/settings.py`); `DEFAULT_FILE_STORAGE` exists only on the pipelines side and disappears in the merge.
2. **Logout is a GET link** (`core/templates/base.html:82`) → `LogoutView` is POST-only in 5.0 (405). Replace with a `<form method="post">` + `{% csrf_token %}`; update the Selenium `test_logout` (`neox/tests/test_schedule_observations.py:71`).
3. `{{form}}` default rendering becomes `<div>`-based in 5.0; only `core/templates/core/uploadreport.html:21` uses it, inside a plain `<form>` → cosmetic, eyeball once.
4. Bumps: `Django>=5.2,<5.3` (5.2.17 current); DRF 3.16 works on 5.2 (3.18 needs ≥5.2); django-reversion 6.3, django-cors-headers 4.9, pytest-django 4.14 declare 5.2; django-storages 1.14.6 and django-dramatiq 0.13–0.15 declare ≤5.1 but only require ≥4.2 → verify.
5. **PostgreSQL ≥14 required** (Q17). Python 3.11 satisfies ≥3.10.
6. Expect new `RemovedInDjango60Warning`s (`CheckConstraint.check`, `URLField.assume_scheme`, positional `Model.save()` args) — warnings only. Run suite, Selenium, `manage.py check --deploy`, dev-namespace deploy.

### 5.2 Releasing `astropy<6.0` — easy in code; the cost is verification (mostly done)

Experiment: main's suite, network off, **astropy 7.2.2 + photutils 2.3.0 + APLpy 2.2.1 + matplotlib 3.8.4 + numpy 1.26.4** vs an identical control on 5.3.4: **1908 tests, one new failure** — `Galactic(...).transform_to(coordinates.ICRS)` passes a frame *class* (removed in 6.0) at `photometrics/SA_scatter.py:79` and `tests/test_SA_scatter.py:56`. The two `AnchoredEllipse` failures disappear (astropy 7 no longer imports it → matplotlib ceiling lifts). No `AstropyDeprecationWarning` under 5.3.4 or 7.2.2. `Frame.wcs` pickles (a pickled `astropy.io.fits.Header`) round-trip 4.2.1/5.3.4 → 7.2.2 and 7.2.2 → 5.3.4 (`docs/migration/wcs_pickles/`). Ceiling on Python 3.11 + numpy 1.x is 7.2.x (astropy 8 needs numpy ≥2).

Silent behaviour changes (no warning) were checked against the extracted changelog (`docs/migration/astropy-api-changes-6.0-7.2.txt`):

| Change (version) | Exposure |
|---|---|
| `CompImageHDU` subclasses `ImageHDU` not `BinTableHDU` (7.0) | no `isinstance(…, BinTableHDU/CompImageHDU)` checks; fpack/funpack sites use `.data`/`.header` only |
| `TableHDU.update` removed (7.0) | the only `.update(` is `Header.update(new_wcs.to_header())` |
| TCTYP/TCUNI/TCRPX/TCRVL/TCDLT special handling dropped (6.0) | FITS-LDAC reading tests pass under 7.2.2 |
| `Table.pformat()` returns all rows (7.0) | only `get_obs.py:70`, already `max_lines=-1`; nothing writes `pformat` to files |
| `Table.meta` is `dict` (7.0) | no `OrderedDict` assumptions |
| `QTable` masked → `MaskedQuantity`; `Time` uses `Masked` (7.0/6.0) | one code `QTable` use, 17 in tests — pass; no `jd2`/NaN reliance |
| `io.ascii` `Reader=/Inputter=/Outputter=` removed (7.0) | not used |
| `Angle` from tuple, `get_moon`, `all_world2pix(accuracy=)` removed | not used |
| Angle/Time string formatting | MPC/ADES formatting is home-grown (pyslalib); `Angle.to_string` only in tests + one site |

Caveats: this exercised main's tests; the pipelines-only FITS/Table code gets the same treatment after the merge (harness in `docs/migration/tools/`, ~6 min). For untested paths use the golden-output regression (gate 8). Recommended hardening: switch `pickle_wcs` to store `header.tostring()` with a legacy-pickle fallback in `unpickle_wcs`.

### 5.3 Later

- **numpy 2:** `ndarray.tostring()` → `tobytes()` (`core/views.py:3916`, `core/tests/test_models.py:3024`), `np.bool8` (`core/property/primitive.py:34`), sweep for repr-dependent string formatting; astropy 7 / photutils 2.3 already support it.
- **Python 3.12:** 45 `assertEquals`-style aliases → `assertEqual`, 95 `datetime.utcnow()` warnings, matplotlib ≥3.7.5; pyslalib is fine (meson). Check the RHEL 9 lifecycle for `python3.11` vs `python3.12` (Q13).
- **bokeh:** 2.3.0 → 2.4.3 first (drops Jinja2/MarkupSafe pins; update the BokehJS CDN tags in `body_detail.html`, `plot_lc.html`, `plot_spec.html`, `calibsource_detail.html`), then the 3.x rewrite of `core/plots.py`.
- Selenium 4 (`find_element_by_*` removed); BeautifulSoup `findAll` → `find_all` (`astrometrics/sources_subs.py`, 5 sites); drop `six`.
- apophis2 replacement is a risk item independent of this merge.

## 6. Appendix index

See `docs/migration/README.md`. Resume notes: Serena memories `migration-pipelines-to-main`, `neoexchange-environments-and-hosts`. Scratch worktrees used for the measurements (`wt-merge` with the trial merge in progress, `wt-main`, `wt-pipelines`) and the scratch venvs live under the session scratchpad in `/tmp` and are not part of the repository.
