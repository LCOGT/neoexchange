# NEO Exchange

Portal for scheduling observations of NEOs using LCOGT

## History

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
