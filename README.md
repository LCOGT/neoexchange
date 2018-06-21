## NEO Exchange

Portal for scheduling observations of NEOs using Las Cumbres Observatory.

## History

### 2.5.0
Create a characterization page for spectroscopy support
* Pull out targets of interest.
* Check of previous spectroscopy from SMASS and MANOS.
* Calculate observing window for the next 3 months for each target.

### 2.4.1

* Change default binning for 0.4m's to bin 1x1.
* Change default proposals for 2018B semester.
* Switch from OpBeat to Rollbar.

### 2.4.0

Add basic spectroscopy support to NEOexchange:
* Added a SNR estimator which can transform the predicted V mag to a variety of different magnitudes for several different taxonomic types (SDSS-i and a Mean taxonomic class is assumed right now) and include the effects of the Moon and zodiacal light. The SNR estimator includes a generalized telescope and instrument model which can be adapted to other telescopes/instruments in the future.
* Added ability to submit spectroscopic observations and associated calibrations to the LCO Network.

### 2.3.6

Bite the Bullet and Update to Python 3.6

### 2.2.0

Added capability of requesting multiple filters when making a user request. 

### 2.1.6

Reduce connection maximum age to 60 seconds. Switch off perturbations in ephemeris computation calls.

### 2.1.5

Update Selenium to 3.11 and Django to 1.11. Refactor functional tests for Valhalla/JavaScript-based authentication. Add functionality to ingest targets from text file list of target names.

### 2.1.4

Better separate Block Registration from SuperBlock Registation so that Blocks only see frames taken during that individual Block and Block times are separate from SuperBlock Start and End times.

### 2.1.3

Add support and new object type for hyperbolic asteroids such as A/2017 U7 and A/2018 C2. Increase ephemeris spacing to 15 mins prevent timeouts.

### 2.1.2

Add support for the 0.4m telescopes at Cerro Tololo, Sutherland and McDonald.

### 2.1.1

Fix for missing absolute magnitudes breaking the diameter calculation.

### 2.1.0

Fixes for non-cadence submitting. Improved error message passthrough from scheduling endpoints. Fixes for block reporting. First part of spectroscopy support for storing spectral taxonomies.

### 1.9.0

Add cadence support.

### 1.8.3

Add check for and marking of 'was not a minor planet' in the Previous NEOCP page
as spacecraft. 
Fixes for POND submitted blocks and lightcurve extraction.
Changes for the new semester boundaries.

### 1.8.2

Bug fix for zooming Analyser view. Feature update on making markers for candidates clickable.

### 1.8.1

New MPC site codes for the second 0.4m telescopes at Tenerife and Maui.

### 1.8.0

- Adding ability to push candidates to Agent NEO on the Zooniverse platform
- Change ReqDB observation submission to Valhalla API submission

### 1.7.2

New MPC site code (Q58) for the 0.4m telescope at Siding Spring. Use case-sensitive searches for updating NEOCP Bodies.

### 1.7.1

Bug fixes in zeropoint determination for newer versions of astroquery. Deploy mtdlink into the container.

### 1.7.0

Astrometry in the browser

### 1.6.9

Change overheads for Sinisto observations. Handle scheduling problems at semester changover at CPT.

### 1.6.8

Cleanups for leaner docker containers.

### 1.6.7.1

Lower the default IPP values. Round arc and not-seen values on the home page.

### 1.6.7

Trap the submission of objects that have no visibility windows.

### 1.6.6

Fix for incorrect revisions being created and clean up script

### 1.6.5

Add fix and trap for a site which has no working telescopes.

### 1.6.4

Addition of 0.4m telescope support.

### 1.6.0-1.6.3

Internal version numbers during addition of 0.4m telescope support.

### 1.5.5

Switch over telescope at Cerro Tololo (W85) to Sinistro. Increase the InterProposal Priority (IPP) value for requests at McDonald (V37). Switch imports to newer pySLALIB module.

### 1.5.4

Update for LCO rebranding.

### 1.5.3

Switch over 2 telescopes at South Africa (K91 & K92) to Sinistro. Filter out proposals with <10 blocks from the block efficiency plot.

### 1.5.2

### 1.5.1

Correct a long-running problem where we didn't correct the Frame midpoint for
half of the exposure time for our own frames. Store FWHM in the Frame objects
when creating.

### 1.5.0

Django 1.10 release

### 1.4.6
Prevent creation of Bodies without orbital elements. Add 0.4m site codes for
proper attribution when creating frames. Fix missing `.fits` extensions in archive
replies when creating Frames.

### 1.4.5
Fix for Arecibo object parsing.

### 1.4.4
Adding short delay when polling MPC for object info.

### 1.4.3
Adding support for new Sinistro (K93) camera at CPT

### 1.4.2
Better comet handling

### 1.4.1
Better support for new request and frame APIs

### 1.4.0
- Adding support for new request and frame APIs

### 1.3.0
- Restructuring frame parsing out of `views.py`

### 1.2.5alpha
- Moon phase on homepage
