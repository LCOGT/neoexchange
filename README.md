# NEO Exchange

Portal for scheduling observations of NEOs using LCOGT

## History

### 1.4.7
Correct a long-running problem where we didn't correct the Frame midpoint for
half of the exposure time for our own frames. Store FWHM in the Frame objects
when creating.

### 1.4.6
Prevent creation of Bodies without orbital elements. Add 0.4m site codes for
proper attribution when creating frames. Fix missing .fits extensions in archive
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
