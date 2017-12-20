'''
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2017-2017 LCO

photometry_subs.py -- Code for photometric transformations.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''

from math import sqrt

from astropy import units as u
from astropy.constants import c, h

def transform_Vmag(mag_V, passband, taxonomy='Mean'):
    '''
    Returns the magnitude in <passband> for an asteroid with a V amgnitude of
    <mag_V> and a taxonomic class of [taxonomy]. If the taxonomy is not given,
    a 'Mean' is assumed
    Taxonomy can be one of:
    'solar' - assuming solar colors (used by the MPC?),
    'mean'  - average of the S- and C-types is used,
    'neo'   - average weighted by the occurence fraction among NEOs,
    's', 'c', 'q', 'x' - individual taxonomies

    Table 2. Asteroid magnitude transformations from Pan-STARRS1 AB filter magnitudes to the
    Johnson-Cousin V system based on Tonry et al. (2012). Solar colors are also included for
    reference.
    Taxonomy   	V-gP1   V-rP1   V-iP1   V-zP1   V-yP1   V-wP1
    Sun	        -0.217  0.183   0.293   0.311   0.311   0.114
    Q           -0.312  0.252   0.379   0.238   0.158   0.156
    S           -0.325  0.275   0.470   0.416   0.411   0.199
    C           -0.238  0.194   0.308   0.320   0.316   0.120
    D           -0.281  0.246   0.460   0.551   0.627   0.191
    X           -0.247  0.207   0.367   0.419   0.450   0.146

    Mean (S+C)   -0.28  0.23    0.39    0.37    0.36    0.16

    According to Binzel et al. in _Asteroids IV_, p. 246:
    "About 90% of the known NEOs fall in the S-, Q-, C- and X-complexes
    with S- (50%), C- (15%), X- (10%) and Q- (10%) types dominating."
    '''


    mag_mapping = { 'SOLAR' : {'r' : 0.183, 'i' : 0.293, 'w' : 0.114 },
                    'MEAN'  : {'r' : 0.230, 'i' : 0.390, 'w' : 0.160 },
                       'S'  : {'r' : 0.275, 'i' : 0.470, 'w' : 0.199 },
                       'C'  : {'r' : 0.194, 'i' : 0.308, 'w' : 0.120 },
                       'Q'  : {'r' : 0.252, 'i' : 0.379, 'w' : 0.156 },
                       'X'  : {'r' : 0.207, 'i' : 0.367, 'w' : 0.146 },
                     'NEO'  : {'r' : 0.213, 'i' : 0.356, 'w' : 0.148 },
                  }

    # Lookup taxonomy to try and get V-<passband> color terms
    color_terms = mag_mapping.get(taxonomy.upper(), None)

    # If we got a sucessful taxonomy lookup, try to lookup the <passband>
    # in the color terms
    delta_mag = None
    if color_terms:
        delta_mag = color_terms.get(passband, None)

    new_mag = None
    if delta_mag:
        new_mag = mag_V - delta_mag

    return new_mag

def compute_photon_rate(mag, tic_params, emulate_signal=False):
    '''Compute the number of photons/s/cm^2/angstrom for an object of magnitude
    <mag> in a specific passband.
    The result is returned as a `~astropy.units.Quantity` object or None if this
    can't be calculated. If [emulate_signal] is set to True, then it will use a
    lower precision value of h (Planck's constant) to emulate the IAC's SIGNAL
    code (http://catserver.ing.iac.es/signal/)

    In order to work, this routine need a dictionary, <tic_params>, for the
    telecope, instrument, camera parameters. For this routine, the needed entries
    are:
        'flux_mag0'  : the flux in Janskys of a mag=0 object in this band (u.Jy)
        'wavelength' : the central wavelength of the band involved (normally u.nm,
                       although astropy.units wavelength should work)
    '''

    if emulate_signal:
#   Equivalent original code below
#   6.6 magic no .is the mantissa part of Planck's constant(rounded). Most of the
#   exponent part (10^-34) is cancelled by Jansky->erg conversion (10^-23) and
#   erg->Watts (10^-7)
#       m_0 = tic_params['flux_mag0'] * 10000.0/6.6/tic_params['wavelength']

# Need new version of h at same low precision as SIGNAL's original code
        hc = (6.6e-27 * h.cgs.unit) * c.to(u.angstrom / u.s)

# Photon energy in ergs/photon
        photon_energy = (hc / tic_params['wavelength'].to(u.angstrom))/u.photon

# Convert flux in Janskys (=10^-23 ergs s^-1 cm^-2 Hz^-1) to an energy density per second
        energy_density = tic_params['flux_mag0'].to(u.erg/(u.s*u.cm**2*u.Hz)) * tic_params['wavelength'].to(u.Hz,equivalencies=u.spectral())

# Divide by the energy-per-photon at this wavelength and the wavelength to give us
# photons per second per cm**2 per Angstrom, matching the astropy version below
        m_0 = energy_density / photon_energy / tic_params['wavelength'].to(u.AA)
    else:
        m_0 = tic_params['flux_mag0'].to(u.photon / u.cm**2 / u.s / u.angstrom, equivalencies=u.spectral_density(tic_params['wavelength']))

    rate = None
    try:
        rate = m_0*10.0**(-0.4*mag)
    except TypeError:
        pass

    return rate

def compute_floyds_snr(mag_i, exp_time, zp_i=24.0, sky_mag_i=19.3, sky_variance=2, read_noise=3.7, dbg=False, emulate_signal=False):
    '''Compute the per-pixel SNR for FLOYDS based on the passed SDSS/PS-i'
    magnitude (mag_i) for the given exposure time <exp_time>.
    The i' band zeropoint [zp_i] (defaults to 24.0) that gives 1 electron/pixel/s,
    the sky variance and the readnoise [read_noise] (defaults to 3.7e-/pixel)
    are also needed.
    Extinction and variation with airmass are not included nor is the (neglibile)
    dark current'''

    pixel_scale = 6.0/14.4
    # Photons per second from the source
    m_0 = 10.0 ** ( -0.4 * (mag_i - zp_i))

    signal = m_0 * exp_time

    sky =  10.0 ** ( -0.4 * (sky_mag_i - zp_i))
    if dbg: print signal, sky
    sky = sky / pixel_scale**2
    noise = signal + (sky * exp_time) + read_noise**2
    noise = sqrt(noise)
    snr = signal / noise

    return snr
