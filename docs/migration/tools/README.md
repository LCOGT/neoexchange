# Migration verification tools

- `run_tests.sh <worktree> <python> <logfile> [apps...]` — run the Django suite in a worktree with a given interpreter, `-v 2`, timed.
- `run_tests_nonet_warn.sh <worktree> <python> <logfile> [apps...]` — same, but with the network disabled (`unshare -rn`) and `PYTHONWARNINGS=always`, so network-dependent tests fail fast and every deprecation warning is logged. Compare two logs with `parse_failures.py`.
- `parse_failures.py <logfile>` — summarise FAIL/ERROR by exception type and test class.
- `install311_asis.sh` — reproduce the "does the pipelines requirements.txt install under /usr/bin/python3.11" experiment (`SCRATCH`, `REPO` env vars).
- `install_astropy7.sh` — build a venv from main's requirements with astropy 7.x / photutils 2.x / APLpy 2.2.1 / matplotlib 3.8 substituted.
- `wcs_pickle_make.py <tag>` / `wcs_pickle_load.py` — pickle a FITS header the way `core.models.frame.pickle_wcs` does under one astropy and load it under another (run from the repo root; pickles in `../wcs_pickles/`).
