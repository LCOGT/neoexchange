## NEO Exchange

Portal for scheduling observations of NEOs (and other Solar System objects) using Las Cumbres Observatory.

## History

### 3.10
* Add support for DAMIT and advanced LC plotting features.

### 3.9.0
* Implement DataProducts refactor for ALCDEF, Gifs, and Floyds Traces

### 3.8.13
* Adds galactic plane into the visualization plots.

### 3.8.12
* Adds support for multi-target spectroscopy blocks.

### 3.8.11
* Adds support for the two 1-m telescopes at Tenerife (Issue #555)

### 3.8.10
* Updates gif movies to fix intermitent issues and sort by filter.
* Add error to spectra plots.

### 3.8.9
* Fix issue with an alternative reporting format for artificial satellites which broke the Previous NEOCP page parser.
* Fix rare issue where scheduling form would reset to previous day in cases where there was limited visibility.

### 3.8.8
* Fix issue in error reporting when submitting cadence with no valid requests.
* Allow a specific FTP URL file to be passed for the Yarkovsky fetcher and planner (for when the 'latest' symlink doesn't get updated)

### 3.8.7
* Add support for generating PDS XML labels.
* Add support for fetching Yarkovsky targets from JPL ftp site.

### 3.8.6
* Update spectroscopy analysis capabilities.
* Add new Body method to compute and return distances and use this for the LOOK targets page.

### 3.8.5
Paginate new gif movie page to speed up load times and prevent connection errors

### 3.8.4
* Add observed location to observation timeline.
* Fix bugs and add features for lightcurve extraction.

### 3.8.3
Add support for adding new LOOK project targets.

### 3.8.2
Fix for cadences crossing semester boundaries.

### 3.8.1
Update default exposure time estimate to be instrument agnostic.

### 3.8.0.2
Fix for occasional OSError on LDAC catalogs.

### 3.8.0.1
make Gif creation more robust.

### 3.8.0
Add postgres support.

### 3.7.0
Add MuSCAT3 support and Repeat Exposure for long blocks

### 3.6.2
* Add support for Mt John observatory (MPC site code 474) for ephemeris computation. (Issue #499)
* Add a Time Critical option for scheduling spectroscopy (Issue #500)
* Fix a rare case when position computation using `sla_planel()` fails (Issue #498)

### 3.6.1
Change the retrieval or creation of new Frame records to eliminate chance of creating duplicates.

### 3.6.0
Update to Django 3.1 (and CentOS 8 for the Docker build)

### 3.5.2
Various small backend fixes:
* Fix HORIZONS SPK lookup on some comets (Issue #480)
* Prevent objects inheriting old elements when refitting with `find_orb` fails
* Fix crazy time from perihelion when mean anomaly is extremely close to 0/360.0 (Issue #484)
* Catch various URL connection errors
* Update internal links to SMASS datasets if they change after ingestion (Issue #486)

### 3.5.1.4
Limit Solar Analog spectra to 1 regardless of frames requested for Target
Fix more Server Error Bugs

### 3.5.1.3
A couple bug fixes

### 3.5.1.2
Implement lc_plot fix to read in comet mags from Horizons.

### 3.5.1.1
Fix creation of hours-up plots (Due to a need to work around [astropy/numpy bug](https://github.com/astropy/astropy/issues/9374) with filtering on `datetime`s in AstroPy `Table`s with AstroPy >= 3.2.2)

### 3.5.1
* Allow editing of window for spectroscopic calibration targets.
* Fix for incorrect slot length calculation with multiple spectra exposures.
* Upgrades astropy minimum version to 3.2.3 for updated USNO Earth Orientation Parameter URLs and also the minimum version that works on python 3.8
* Adds storage of the orbit RMS from MPC DB
* LOOK Project updates:
  * Adds storage of reciprocal semi-major axis from MPC DB as a PhysicalParameter
  * Adds additional Body attribute to return reciprocal semi-major axis
  * Adds new get_cadence_info() method to summarize whether an object's cadence is underway or has halted and adds this into the LOOK Project template
* Allow search of static (sidereal) calibration sources.

### 3.5.0
Add Light curve analysis tools
* active plotting of light curves
* uploading and displaying annotated gifs for images
* automatic light curve extraction for all image sets
* uploading ALCDEF files to S3

### 3.4.1
Add Parallactic angle option for spectroscopic observations.

### 3.4.0
Update Photometry to use GAIA-DR2

### 3.3.2
Initial support for the LCO Outbursting Objects Key (LOOK) Project

### 3.3.0
* Send proper motion details for solar analogs through to the LCO observing system.
* Display the most recent time of ingest or update on the Body details page.
* Truncate observing windows by the object's visibility as well as the site's darkness times.
* Warn about scheduling of objects that would fail lunar distance constrains before submitting.
* Fix the light curve extraction code to work with comet names
* Refactor all the Django models into separate domain-specific files.

### 3.2.9
Add ability to cancel observations.

### 3.2.8
* Add 2x2 binning & central chip section mode suppport (for faster readout on speedy rocks).
* Fix table parsing of Arecibo targets.

### 3.2.7
* Allow ingestion of numbered comet and comet fragment observations.
* Fix various time out issues with prefetching.
* Update pagination format.
* Fix parsing of comets in Arecibo target lists.
* Add ability to query HORIZONS for comets which have multiple element sets/target bodies available.

### 3.2.6.1
Index frequently used model fields.

### 3.2.6
Fix broken spectra plot
Update Minimum Django Requirements

### 3.2.5
Fix a rare comet bug.

### 3.2.4
Fix a few rare bugs.

### 3.2.3
Allow Time Critical observations within the same proposal and allow selection of this from the scheduling form.

### 3.2.2
Add observation timeline.

### 3.2.0
Add models for physical parameters and Designations
*Includes specific model for colors
*Search includes any of a body's several designations
*Does not remove anything from the Body model

### 3.1.1
Convert Spectroscopy plots into Bokeh for added interactivity.

### 3.0.5
Fix lingering tests for the LCO Request V3 language change

### 3.0.4
Change to LCO Request V3 language

### 3.0.3
Add long-term planning plots showing how the sky position, helio/geocentric distance, magnitude, elongation, Moon-object separation and Moon phase, positional uncertainty and visibility and on-sky rate of motion change with time.

### 3.0.2
Minor bug fixes

### 3.0.1
Minor bug fixes

### 3.0.0
Support for deploying into Amazon Web Services (AWS) using Kubernetes and Helm

### 2.8.9
Add support for the ELP Dome B 1-meter telescope.

### 2.8.6
Change URL scheme for new prefix

### 2.8.5
Modifications to scheme on refitting elements.

### 2.8.4
Add support for displaying log Flux plots of spectrophotometric standards with CTIO/HST/Oke spectra. Add view to show best calibration sources for the telescopes for the current night.

### 2.8.3
* Enhance guide movie creation.
* Allow for graceful failure when outside web endpoints are down.

### 2.8.2
Add ADES PSV export and MPC1992 and ADES PSV download options.

### 2.8.1
Several small updates and fixes
* Improve tests for updated firefox
* Remove gaps between RADAR target ingest & orbit update
* Add error handling for spectroscopy when a 2m isn't available

### 2.8.0
Improve Static Source Scheduling
* Add features to Calib Scheduling Confirmation page to bring it up to date with standard version.
* Add warning for potentially saturated targets.
* Add Tests for Calib scheduling confirmation page
* Add Solar Analog details to NEO scheduling confirmation page
* Make exposure time calculator for Spectroscopic observations of Solar Analogs

### 2.7.13
Calculate frame midpoint based on UTSTOP rather than EXPTIME. Improve ingestion of new objects and record and output discovery asterisks.

### 2.7.12
Output of compute_ephem is now a dictionary.

### 2.7.11
Allow for automatic updating of targets.
* Update observations from MPC daily.
* Update orbits with FindOrb or from MPC daily.
* Be smarter about when and how FindOrb updates an orbit.
* Update taxonomy daily.
* Update external spectroscopy weekly.

### 2.7.10
Several bug fixes
* Allow Download for all Programs
* Allow for no visible ephemeris for very close objects
* Fix data pull from Arecibo page

### 2.7.9
Improve Cadence scheduling
* Default end-date is current date + 24 hours
* Adjust jitter/Period from the confirmation page
* Handle bad dates rather than crashing
* Various warnings and tips to help with scheduling

### 2.7.8
Comet elements are now selected based on nearest in time.

### 2.7.7
Several patches for tests and minor issue fixes

### 2.7.6
Add Generic Telescope Classes

### 2.7.5
Update the scheduling interface to allow for more options
* Display UT time on website
* Display Site/Telescope class on Confirmation page
* Display Visibility of requested target
* Allow for Exposure time Adjustment
* Display Moon info
* Adjust Max Airmass
* Adjust IPP
* Adjust Minimum Moon Distance
* Adjust Acceptability Threshold

### 2.7.4

Improve the cross-identification code for multiply desiginated objects and periodic comets.

### 2.7.3

Fix issues with interactions between FindOrb and candidates/comets
* Remove Perturbation Code


### 2.7.2

Spectroscopic Graphical tools
* Create and display a gif of the guidefreames during an observation
* Create and display a spectroscopic trace based on the reduced data

### 2.7.1

Add latitude, longitude, height for 0m4b at Tenerife (Z17). Update find_orb build procedure.

### 2.7.0

Flux Standards
* Add Static Source Model to hold flux, spectral, solar and RV standards.
* Add Calibrations List page.
* Add Calibration detail descriptions.
* Allow for sorting out and scheduling spectra for Solar analogs.

### 2.6.0

Calculate and forward more precise orbital elements for spectroscopic observations.

### 2.5.3

Update light curve extraction.
* Pull from Tracking Number rather than block number
* Capable of incorporating any number of blocks for a given target within a given time frame.
Add motion details to characterization page.

### 2.5.2

Robotic scheduler and low-level ToO support.

### 2.5.1
Add block record keeping for spectroscopy.

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
