# docs/migration — evidence for MIGRATION_PLAN.md

| File | Contents |
|---|---|
| `conflicts.md` | trial-merge conflict table, hunk anatomy, duplicated definitions |
| `test-baselines.md` | all baseline/treatment test runs and cross-references |
| `failing-tests-pipelines-py39.txt` | 115 failing tests on `pipelines` (Python 3.9; identical on 3.11) |
| `failing-tests-main-py311.txt` | 25 failing tests on `origin/main` (Python 3.11, network on) |
| `failing-tests-pipelines-only.txt` | the 18 pipelines-only failures |
| `failing-tests-both-branches.txt` | the 16 environment failures shared by both branches |
| `network-dependent-tests.txt` | 33 tests that need the network |
| `astropy7-only-failures.txt` | the single new failure under astropy 7.2.2 |
| `astropy-api-changes-6.0-7.2.txt` | astropy changelog extract (io.fits, table, units, time, wcs, coordinates, …) |
| `rocky9-package-availability.txt` | EPEL 9 / LCO repo availability of the reduction binaries; `python3` inside the Rocky 9 image |
| `python311-wheel-glibc-check.txt` | which Python 3.11 wheels still support glibc 2.17 (CentOS 7 / apophis2) |
| `wcs_pickles/` | header pickles produced under astropy 4.2.1 / 5.3.4 / 7.2.2 |
| `tools/` | scripts used for the runs above |
