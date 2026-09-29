# Test baselines (2026-09-28, this workstation: Rocky 9.8, scamp 2.13.1, sextractor 2.28.2, swarp 2.41.5, gnuastro 0.21, no mtdlink, no redis)

All runs: `python manage.py test core astrometrics photometrics --noinput -v 2` in detached scratch worktrees (Selenium `neox/` tests not run).

| Run | Environment | Result | Notes |
|---|---|---|---|
| pipelines @ py3.9 | `neocode39_psfphot_venv` (Django 3.1.14, numpy 1.23.5, astropy 5.3.4) | 1761 ran, **73 F + 50 E** (115 distinct), 17 skipped, 129 s | `astrometrics/tests/test_ephem_subs.py` fails to import (`NameError: SimpleTestCase`, since c2b43b92 Jan 2026) → ~229 tests not executed |
| pipelines @ py3.11, same pins | scratch venv from unchanged `requirements.txt` | 1761 ran, **identical failing set** | pyslalib 1.0.10 built via meson; matplotlib 3.5.1 built from source |
| main @ py3.11, network on | `neocode311_venv` (Django 4.2.27, numpy 1.26.4, astropy 5.3.4, mpl 3.10.0) | 1908 ran, **3 F + 23 E**, 14 skipped, 45 min | 21 network (Vizier 504/timeouts), 3 binary-version, 2 matplotlib-3.10 (`AnchoredEllipse` via astropy 5.3.4 WCSAxes) |
| main @ py3.11, **no network** (control) | same venv, `unshare -rn`, `PYTHONWARNINGS=always` | 1908 ran, 37 failing, 424 s | only Django deprecation: `USE_L10N` (RemovedInDjango50Warning); no AstropyDeprecationWarning |
| main @ py3.11, **astropy 7.2.2** (treatment) | scratch venv: astropy 7.2.2, photutils 2.3.0, APLpy 2.2.1, matplotlib 3.8.4, numpy 1.26.4, Django 4.2.30 | 1908 ran, 36 failing, 325 s | 35 common with control; **1 new** (`SA_scatter` `transform_to(ICRS)` class → instance); 2 fixed (`AnchoredEllipse`) |

Cross-references:
- ≈96 of the 115 pipelines failures exist on main by method name and pass there → resolved by taking main's side in the merge.
- 18 fail only on pipelines → `failing-tests-pipelines-only.txt`.
- 16 fail on both branches → `failing-tests-both-branches.txt` (environment).
- 33 tests need the network → `network-dependent-tests.txt` (14 `ZeropointUnitTest`, 6 `StoreCatalogSourcesTest`, 1 `TestGetReferenceCatalog`, 12 PDS tests that resolve target names online).

Other deprecation warnings raised from project code (future numpy 2 / Python 3.12 work): `ndarray.tostring()` (`core/views.py:3916`, `core/tests/test_models.py:3024`), `np.bool8` (`core/property/primitive.py:34`), BeautifulSoup `findAll` (5 sites in `astrometrics/sources_subs.py`), `assertEquals` (45 occurrences in 6 test files).

WCS pickle round-trip (`Frame.wcs` = pickled `astropy.io.fits.Header`, protocol 2, base64): headers pickled under astropy 4.2.1 and 5.3.4 load and give identical `WCS` solutions under 7.2.2; 7.2.2 pickles load under 5.3.4 → upgrade and rollback safe. Scripts: `tools/wcs_pickle_make.py`, `tools/wcs_pickle_load.py`.
