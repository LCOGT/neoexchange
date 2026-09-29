# Trial merge: conflicts (origin/main@0babdc61 <- pipelines@8d32e1c8)

Generated 2026-09-28 with `git merge --no-commit --no-ff pipelines` on a detached worktree of origin/main.

Status summary: 97 added, 31 modified, 7 deleted, 30 content conflicts (UU), 1 modify/delete (UD: `core/management/commands/download_archive_data.py` deleted on pipelines, modified on main — keep main's, its FLOYDS cron uses it), 1 add/add (AA: `photometrics/lightcurve_subs.py`).

## Conflict hunks per file

| hunks | conflict lines | file |
|---:|---:|---|
| 18 | 659 | `neoexchange/photometrics/tests/test_catalog_subs.py` |
| 13 | 599 | `neoexchange/photometrics/pds_subs.py` |
| 9 | 261 | `neoexchange/photometrics/external_codes.py` |
| 8 | 5794 | `neoexchange/photometrics/tests/test_pds_subs.py` |
| 6 | 63 | `neoexchange/astrometrics/ephem_subs.py` |
| 6 | 572 | `neoexchange/core/views.py` |
| 6 | 50 | `neoexchange/photometrics/catalog_subs.py` |
| 5 | 810 | `neoexchange/core/tests/test_views.py` |
| 4 | 994 | `neoexchange/photometrics/tests/test_external_codes.py` |
| 4 | 37 | `neoexchange/requirements.txt` |
| 4 | 35 | `neoexchange/astrometrics/sources_subs.py` |
| 4 | 32 | `neoexchange/photometrics/lightcurve_subs.py` |
| 4 | 32 | `neoexchange/photometrics/gf_movie.py` |
| 4 | 29 | `neoexchange/core/models/blocks.py` |
| 4 | 20 | `neoexchange/astrometrics/tests/test_ephem_subs.py` |
| 3 | 255 | `neoexchange/core/tests/test_models.py` |
| 2 | 39 | `Dockerfile` |
| 2 | 15 | `neoexchange/core/forms.py` |
| 2 | 14 | `neoexchange/astrometrics/site_config.py` |
| 2 | 130 | `neoexchange/neox/urls.py` |
| 2 | 11 | `neoexchange/neox/settings.py` |
| 2 | 11 | `neoexchange/core/models/frame.py` |
| 2 | 10 | `neoexchange/astrometrics/tests/test_sources_subs.py` |
| 1 | 83 | `README.md` |
| 1 | 7 | `neoexchange/core/frames.py` |
| 1 | 7 | `neoexchange/core/archive_subs.py` |
| 1 | 5 | `neoexchange/photometrics/tests/test_spectraplot.py` |
| 1 | 5 | `neoexchange/core/models/sources.py` |
| 1 | 5 | `neoexchange/core/management/commands/lightcurve_extraction.py` |
| 1 | 5 | `neoexchange/core/admin.py` |
| 1 | 13 | `neoexchange/core/models/body.py` |
| 0 | 0 | `neoexchange/core/management/commands/download_archive_data.py` |

**Totals: 124 hunks, 10,602 lines inside conflict markers, 32 files.** Six files hold ~80% of the volume.

## Hunk anatomy of the largest files (ours = main lines, theirs = pipelines lines)

```
## neoexchange/photometrics/tests/test_pds_subs.py
   hunk@9      ours=0     theirs=1    
   hunk@17     ours=1     theirs=2    
   hunk@28     ours=3     theirs=0    
   hunk@244    ours=3002  theirs=0    
   hunk@3307   ours=0     theirs=2000 
   hunk@5314   ours=1     theirs=0    
   hunk@5327   ours=6     theirs=3    
   hunk@7753   ours=102   theirs=649  
## neoexchange/photometrics/tests/test_external_codes.py
   hunk@30     ours=2     theirs=5    
   hunk@562    ours=3     theirs=0    
   hunk@577    ours=8     theirs=1    
   hunk@1977   ours=90    theirs=873  
## neoexchange/core/tests/test_views.py
   hunk@28     ours=1     theirs=3    
   hunk@1171   ours=11    theirs=6    
   hunk@1196   ours=0     theirs=3    
   hunk@1208   ours=11    theirs=9    
   hunk@9252   ours=76    theirs=675  
## neoexchange/photometrics/tests/test_catalog_subs.py
   hunk@803    ours=2     theirs=2    
   hunk@833    ours=2     theirs=2    
   hunk@863    ours=2     theirs=2    
   hunk@924    ours=2     theirs=2    
   hunk@955    ours=2     theirs=2    
   hunk@1341   ours=8     theirs=36   
   hunk@1686   ours=21    theirs=30   
   hunk@1754   ours=0     theirs=100  
   hunk@2156   ours=0     theirs=1    
   hunk@2205   ours=0     theirs=1    
   hunk@2256   ours=0     theirs=1    
   hunk@2307   ours=0     theirs=1    
   hunk@2358   ours=0     theirs=1    
   hunk@2409   ours=0     theirs=1    
   hunk@2460   ours=0     theirs=1    
   hunk@2511   ours=0     theirs=1    
   hunk@4639   ours=0     theirs=346  
   hunk@5137   ours=0     theirs=36   
## neoexchange/photometrics/pds_subs.py
   hunk@15     ours=13    theirs=6    
   hunk@963    ours=1     theirs=0    
   hunk@984    ours=5     theirs=4    
   hunk@1000   ours=17    theirs=2    
   hunk@1071   ours=1     theirs=1    
   hunk@1080   ours=1     theirs=1    
   hunk@1302   ours=10    theirs=5    
   hunk@1370   ours=163   theirs=0    
   hunk@1561   ours=50    theirs=0    
   hunk@1632   ours=1     theirs=1    
   hunk@1650   ours=1     theirs=1    
   hunk@1662   ours=1     theirs=1    
   hunk@1729   ours=274   theirs=0    
## neoexchange/core/views.py
   hunk@24     ours=5     theirs=4    
   hunk@3658   ours=1     theirs=1    
   hunk@4909   ours=3     theirs=0    
   hunk@4919   ours=4     theirs=5    
   hunk@5023   ours=1     theirs=1    
   hunk@5083   ours=0     theirs=529  
## neoexchange/photometrics/external_codes.py
   hunk@30     ours=4     theirs=7    
   hunk@903    ours=2     theirs=2    
   hunk@1392   ours=1     theirs=8    
   hunk@1408   ours=1     theirs=3    
   hunk@1518   ours=13    theirs=29   
   hunk@1576   ours=1     theirs=6    
   hunk@1731   ours=99    theirs=0    
   hunk@1922   ours=16    theirs=1    
   hunk@1964   ours=41    theirs=0    
## neoexchange/core/tests/test_models.py
   hunk@1555   ours=63    theirs=146  
   hunk@3133   ours=1     theirs=1    
   hunk@3164   ours=4     theirs=31   
```

## Definitions that appear on both sides of hunks (semantic, not textual, resolution)

- `photometrics/external_codes.py`: `run_sextractor`, `convert_file_to_crlf` defined on both sides → dedupe.
- `core/views.py`: `run_sextractor_make_catalog` defined on both sides → dedupe.
- `photometrics/tests/test_pds_subs.py`: the same 12 test classes (`TestCreateDisciplineArea`, `TestCreateDisplaySettings`, `TestCreateFileAreaBinTable`, `TestCreateFileAreaObs`, `TestCreateFileAreaTable`, `TestCreateImageArea`, `TestCreateImgDispGeometry`, `TestExportBlockToPDS`, `TestMakePDSAsteroidName`, `TestPreambleMapping`, `TestSplitFilename`, `TestWritePDSLabel`) were added on both sides at different positions (hunk@244 main=3002 lines vs hunk@3307 pipelines=2000) → resolve class-by-class, not hunk-by-hunk.
- `photometrics/tests/test_external_codes.py`, `core/tests/test_views.py`, `photometrics/tests/test_catalog_subs.py`: pipelines-side additions of whole test classes; duplicated `setUp`/`test_1` names are within different classes.

## The 24 small files

Mechanical: ELP Aqawan-B MPC codes (`V45`/`V47` on main are the real assigned codes; `V98`/`V99` on pipelines were temporary) in `ephem_subs.py`, `sources_subs.py`, `site_config.py`, `forms.py`, `models/frame.py`; import lists; docstrings; `set_auto_axislabel` try/except (main) in `gf_movie.py`; `unpack_sci_extension` (main) vs `funpack_fits_file(all_hdus=…)` (pipelines) in `catalog_subs.py`; `Frame.NEOX_SUB_FRAMETYPE = 93`, `NONLCO_SITES`, MRO/H01 and SOAR/I33 sites, MRO archive paths (pipelines additions to keep).
