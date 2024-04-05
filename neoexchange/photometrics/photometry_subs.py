"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2017-2024 LCO

photometry_subs.py -- Code for photometric transformations.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from math import sqrt, log10, sin, cos, exp, acos, radians, degrees, erf, log
import logging

import numpy as np
from astropy import units as u
from astropy.io import fits
from astropy.table import vstack
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
from astropy.constants import c, h
from astropy.coordinates import SkyCoord

logger = logging.getLogger(__name__)


def transform_Vmag(mag_V, passband, taxonomy='Mean'):
    """
    Returns the magnitude in <passband> for an asteroid with a V magnitude of
    <mag_V> and a taxonomic class of [taxonomy]. If the taxonomy is not given,
    a 'Mean' is assumed
    Taxonomy can be one of:
    'solar' - assuming solar colors (used by the MPC?),
    'mean'  - average of the S- and C-types is used,
    'neo'   - average weighted by the occurrence fraction among NEOs,
    's', 'c', 'q', 'x' - individual taxonomies

    Table 2. Asteroid magnitude transformations from Pan-STARRS1 AB filter magnitudes to the
    Johnson-Cousin V system based on Veres et al. (2015). Solar colors are also included for
    reference.
    Taxonomy    V-gP1   V-rP1   V-iP1   V-zP1   V-yP1   V-wP1
    Sun         -0.217  0.183   0.293   0.311   0.311   0.114
    Q           -0.312  0.252   0.379   0.238   0.158   0.156
    S           -0.325  0.275   0.470   0.416   0.411   0.199
    C           -0.238  0.194   0.308   0.320   0.316   0.120
    D           -0.281  0.246   0.460   0.551   0.627   0.191
    X           -0.247  0.207   0.367   0.419   0.450   0.146

    Mean (S+C)   -0.28  0.23    0.39    0.37    0.36    0.16

    According to Binzel et al. in _Asteroids IV_, p. 246:
    "About 90% of the known NEOs fall in the S-, Q-, C- and X-complexes
    with S- (50%), C- (15%), X- (10%) and Q- (10%) types dominating."
    """

    mag_mapping = { 'SOLAR' : {'g' : -0.217, 'r' : 0.183, 'i' : 0.293, 'z' : 0.311, 'Y' : 0.311, 'w' : 0.114},
                    'MEAN'  : {'g' : -0.28 , 'r' : 0.230, 'i' : 0.390, 'z' : 0.37 , 'Y' : 0.36 , 'w' : 0.160},
                       'S'  : {'g' : -0.325, 'r' : 0.275, 'i' : 0.470, 'z' : 0.416, 'Y' : 0.411, 'w' : 0.199},
                       'C'  : {'g' : -0.238, 'r' : 0.194, 'i' : 0.308, 'z' : 0.320, 'Y' : 0.316, 'w' : 0.120},
                       'Q'  : {'g' : -0.312, 'r' : 0.252, 'i' : 0.379, 'z' : 0.238, 'Y' : 0.158, 'w' : 0.156},
                       'X'  : {'g' : -0.247, 'r' : 0.207, 'i' : 0.367, 'z' : 0.419, 'Y' : 0.450, 'w' : 0.146},
                       'D'  : {'g' : -0.281, 'r' : 0.246, 'i' : 0.460, 'z' : 0.551, 'Y' : 0.627, 'w' : 0.191},
                     'NEO'  : {'g' : -0.254, 'r' : 0.213, 'i' : 0.356, 'z' : 0.322, 'Y' : 0.314, 'w' : 0.148},
                  }

    # Lookup taxonomy to try and get V-<passband> color terms
    color_terms = mag_mapping.get(taxonomy.upper(), None)

    # If we got a successful taxonomy lookup, try to lookup the <passband>
    # in the color terms
    delta_mag = None
    if color_terms:
        delta_mag = color_terms.get(passband, None)

    new_mag = None
    if delta_mag:
        new_mag = mag_V - delta_mag

    return new_mag


def calc_sky_brightness(bandpass, moon_phase, dark_sky_mag=None):
    """Calculates the new sky brightness in the given <bandpass> for the
    given <moon_phase>. The [dark_sky_mag] can be given, or if None, it
    will be determined from a table of defaults (taken from SIGNAL).
    Changes in magnitude with sky brightness come from the IAC and SIGNAL.

    References
    ----------
    http://www.ing.iac.es/Astronomy/observing/conditions/#sky
    """

    sky_mags = default_dark_sky_mags()

    # Passbands redder than V are less affected by moonlight. This list is used to lower
    # the amount of sky brightening later
    red_bands = ['R', 'I', 'Z', 'w', 'rp', 'ip', 'zp']

    sky_mag = None
    if bandpass in sky_mags.keys():
        if dark_sky_mag is None:
            dark_sky_mag = sky_mags[bandpass]
        moon_phase = moon_phase.upper()
        delta = 0.0
        if moon_phase == 'D':
            delta = 0.4
        elif moon_phase == 'G':
            delta = 2.15
            if bandpass in red_bands:
                delta = 1.3
        elif moon_phase == 'B':
            delta = 3.4
            if bandpass in red_bands:
                delta = 2.7
        sky_mag = dark_sky_mag - delta

    return sky_mag


def sky_brightness_model(params, dbg=False):
    """Calculate a more accurate sky background model based on the
    contributions from the airglow (a function of the solar radio flux,
    zodiacal dust (as a function of ecliptic latitude) and background
    starlight (as a function of galactic latitude"""

    solar_flux = params.get('sfu', 0.8*u.MJy)
    airmass = params.get('airmass', None)
    if airmass is None:
        if params.get('target_zd', None) is not None:
            airmass = compute_airmass(params['target_zd'])
    q_airglow = (145.0+130.0*((solar_flux.to(u.MJy).value-0.8)/1.2))*airmass
    ecliptic_lat = params.get('ecliptic_lat', None)
    galactic_lat = params.get('galactic_lat', None)
    if ecliptic_lat is None or galactic_lat is None:
        if params.get('ra_rad', None) and params.get('dec_rad', None):
            try:
                target = SkyCoord(ra=params['ra_rad']*u.rad, dec=params['dec_rad']*u.rad, frame='icrs')
                ecliptic_lat = target.barycentrictrueecliptic.lat
                galactic_lat = target.galactic.b
                if dbg:
                    print(target, ecliptic_lat, galactic_lat)
            except ValueError:
                logger.warning("Could not find/convert co-ordinates")
    # Assume a value of 60.0 in S10 units for the zodiacal light if the
    # latitude wasn't given or calculable
    q_zodi = 60.0
    if ecliptic_lat:
        if type(ecliptic_lat) == float:
            ecliptic_lat = ecliptic_lat * u.deg
        if ecliptic_lat.to(u.deg).value < 60.0:
            q_zodi = 140.0 - 90.0 * sin(radians(ecliptic_lat.value))

    q_stars = 0.0
    if galactic_lat:
        if type(galactic_lat) == float:
            galactic_lat = galactic_lat * u.deg
        q_stars = 100.0 * exp(-abs(galactic_lat.to(u.deg).value/10.0))
    q = q_airglow + q_zodi + q_stars
    q_format = 'Moonless V sky brightness, in S10 units (equivalent 10th-mag stars/deg^2):\n' +\
        '%6.1f ( = %6.2f airglow + %6.2f zodiacal light + %6.2f starlight)'
    if dbg:
        print(q_format % ( q, q_airglow, q_zodi, q_stars))

    # Determine the difference in sky color between the given bandpass and
    # V band
    default_sky_mags = default_dark_sky_mags()
    sky_color_corr = default_sky_mags.get(params['bandpass'], default_sky_mags['V']) - default_sky_mags['V']
    if dbg:
        print('Color correction', sky_color_corr)
    sky_mag = 27.78-2.5*log10(q) + sky_color_corr
    q_sky = 10.0**((27.78-sky_mag)/2.5)

    q_moon = compute_moon_brightness(params)
    if dbg:
        print('Moonlight', q_moon, ' S10 units')
    q_total = q_sky + q_moon

    sky_mag_all = 27.78-2.5*log10(q_total)

    return sky_mag_all, sky_mag-sky_mag_all


def compute_airmass(zd):
    """Calculate the airmass from the passed zenith distance <zd> (specified
    in degrees). This version behaves properly at large zenith
    distances/high airmasses"""

    return 1.0 / sqrt(1.0-0.96*(sin(radians(zd)))**2.0)


def compute_moon_brightness(params, dbg=False):
    """Calculate the increase in brightness in V due to the Moon via the
    prescription of Krisciunas & Schaefer (1991). The needed keys in the
    <params> dictionary are:
    'moon_target_sep' : separation between the Moon and the target (as a
                        `astropy.units` angle or a float (in degrees)
    'moon_phase'      : Moon Fractional lunar illumination (from ephem_subs.moonphase())
    OR
    'moon_phase_angle' : Lunar phase angle (0 = full, 90 = 7-day old moon, 180 = new moon)
    'moon_zd'         : Zenith distance of the Moon (degrees)
    """

    # For comparison against SIGNAL, uncomment the following (normalization
    # factor for measured values at the Jacobus Kapteyn Telescope (in 1998)
#    fudge = 2.4
    fudge = 1.0

    r = params['moon_target_sep']
    try:
        r = r.to(u.rad).value
    except AttributeError:
        r = radians(r)

    if params.get('moon_phase_angle', None) is not None:
        phi = params['moon_phase_angle']
    else:
        if params.get('moon_phase', None) is not None:
            # Retrieve lunar phase angle
            alpha = acos(1.0-2.0*params['moon_phase'])
            phi = 180.0 - degrees(alpha)
        else:
            logger.error("Need either 'moon_phase_angle' or 'moon_phase' (fractional lunar illumination")
            return None
    # Compute surface brightness of the Moon
    s = 10.0**(-0.4*(3.84+0.026*phi + 4e-9 * phi**4))
    # Compute Rayleigh and Mie scattering
    f_rayleigh = 10.0**5.36*(1.06+(cos(r)**2))
    f_mie = 10.0**(6.15-(degrees(r)/40.0))
    fr = f_rayleigh + f_mie

    moon_airmass = compute_airmass(params['moon_zd'])
    extinct = extinction_in_band('V')
    airmass = params.get('airmass', None)
    if airmass is None:
        if params.get('target_zd', None) is not None:
            airmass = compute_airmass(params['target_zd'])
    if dbg:
        print('airmass, extinct ', airmass, extinct)

    # Calculate background due to Moon in nanoLamberts, convert to S10 units
    bkgd_nl = s * fr * 10.0**(-0.4*extinct*moon_airmass) * (1.0-10.0**(-0.4*extinct*airmass))
    bkgd_s10 = bkgd_nl * 3.8
    if dbg:
        print('s,fr,xz,xzm,bnl,bs10 ', s, fr, airmass, moon_airmass, bkgd_nl, bkgd_s10)
    return bkgd_s10


def compute_photon_rate(mag, tic_params, emulate_signal=False):
    """Compute the number of photons/s/cm^2/angstrom for an object of magnitude
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
    """

    if emulate_signal:
        # Equivalent original code below
        # 6.6 magic no. is the mantissa part of Planck's constant(rounded). Most of the
        # exponent part (10^-34) is cancelled by Jansky->erg conversion (10^-23) and
        # erg->Watts (10^-7)
        # m_0 = tic_params['flux_mag0'] * 10000.0/6.6/tic_params['wavelength']

        # Need new version of h at same low precision as SIGNAL's original code
        hc = (6.6e-27 * h.cgs.unit) * c.to(u.angstrom / u.s)

        # Photon energy in ergs/photon
        photon_energy = (hc / tic_params['wavelength'].to(u.angstrom))/u.photon

        # Convert flux in Janskys (=10^-23 ergs s^-1 cm^-2 Hz^-1) to an energy density per second
        energy_density = tic_params['flux_mag0'].to(u.erg/(u.s*u.cm**2*u.Hz)) * tic_params['wavelength'].to(u.Hz, equivalencies=u.spectral())

        # Divide by the energy-per-photon at this wavelength and the wavelength to give us
        # photons per second per cm**2 per Angstrom, matching the astropy version below
        m_0 = energy_density / photon_energy / tic_params['wavelength'].to(u.AA)
    else:
        m_0 = tic_params['flux_mag0'].to(u.photon / u.cm**2 / u.s / u.angstrom, equivalencies=u.spectral_density(tic_params['wavelength']))

    rate = None
    try:
        rate = m_0*10.0**(-0.4*mag)
    except u.UnitTypeError:
        # astropy.units Quantity, take value
        rate = m_0*10.0**(-0.4*mag.value)
    except TypeError:
        pass

    return rate


def extinction_in_band(tic_params_or_filter):
    """Returns the extinction in the bandpass. <tic_params_or_filter> can either
    be a filter name (e.g. 'I', ip') or a dictionary of telecope, instrument,
    camera parameters, in which case the 'filter' key is used to retrieve the
    bandpass.
    The extinction in magnitudes/airmass is returned or 0.0 (if the bandpass was
    not found)"""

# Extinction values from SIGNAL (for La Palma) for UBVRIZ, 
# Tonry et al. 2012 (divided by 1.2) for u'g'r'i'z'w
    airm = 1.2
    extinction = { 'U': 0.55, 'B': 0.25, 'V' : 0.15, 'R' : 0.09, 'I' : 0.06, 'Z' : 0.05,
                   'gp' : 0.22/airm, 'rp' : 0.13/airm, 'ip' : 0.09/airm, 'zp' : 0.05/airm, 'w' : 0.15/airm}

    obs_filter = tic_params_or_filter
    if type(tic_params_or_filter) == dict:
        try:
            extinction = float(tic_params_or_filter.get('extinction', None))
            return extinction
        except (TypeError, ValueError):
            pass
        obs_filter = tic_params_or_filter.get('filter', None)

    return extinction.get(obs_filter, 0.0)


def calculate_effective_area(tic_params, dbg=False):
    """Calculate effective collecting area of the telescope, instrument & detector
    The effective throughput consists of four terms:
    1) atmospheric transmission (based on extinction/airmass and airmass),
    2) mirror reflectivity (85% for Al assumed unless specified)**no. of of mirrors,
    3) instrument efficiency * scaling factor (1.0 assumed unless specified),
    4) filter or grating efficiency,
    5) CCD detector efficiency (QE)
    """
    extinction = extinction_in_band(tic_params)
    if dbg:
        print("Extinction per airmass (mag), airmass, total ext.   %.3f %.3f %.4f" % (extinction, tic_params.get('airmass', 1.0), extinction*tic_params.get('airmass', 1.0)))

    area = tic_params['eff_area'].to(u.cm**2)
    thru_atm = 10.0**(-(extinction/2.5)*tic_params.get('airmass', 1.0))
    thru_tel = tic_params.get('mirror_eff', 0.85)**float(tic_params.get('num_mirrors', 2))
    thru_inst = tic_params['instrument_eff'] * tic_params.get('true_vs_pred', 1.0)
    if tic_params.get('imaging', False) is True:
        thru_filt_grat = tic_params['filter_eff']
        filt_grat_string = 'filt'
    else:
        thru_filt_grat = tic_params['grating_eff']
        filt_grat_string = 'grat'
    throughput = thru_atm * thru_tel * thru_inst * thru_filt_grat

    if dbg:
        fmt = "Atm*tel*inst*%4s throughput   %.2f =  %.2f *  %.2f *  %.2f *  %.2f"
        print(fmt % (filt_grat_string, throughput, thru_atm, thru_tel, thru_inst, thru_filt_grat))

    area = area * throughput
    area = area * tic_params['ccd_qe']

    return area


def compute_zp(tic_params, dbg=False, emulate_signal=False):

    # Calculate photons/sec/A/cm^2 for mag=0.0 source
    m_0 = compute_photon_rate(0.0, tic_params, emulate_signal)

    # Calculate effective capture cross-section
    eff_area = calculate_effective_area(tic_params, dbg)
    zp = m_0 * eff_area

    # If imaging, multiply by bandwidth of filter. If spectroscopy, just drop angstrom units
    if tic_params.get('imaging', False):
        zp *= tic_params['bandwidth'].to(u.angstrom)
    else:
        zp *= u.angstrom

    # Convert to magnitude
    zp_mag = None
    if zp != 0:
        zp_mag = -u.Magnitude(zp)
        if dbg:
            print('ZP (photons/sec)=', zp)
        if dbg:
            print('ZP (mag+extinct)=', zp_mag)

    return zp, zp_mag


def slit_vignette(tic_params):
    """Compute the fraction of light entering the slit of width <tic_params['slit_width']>
    for an object described by a FWHM of <tic_params['fwhm']>
    In the case of imaging mode, 1.0 is always returned.

    The code is taken from the IAC/Chris Benn's SIGNAL code (`slitvign` routine):
    http://www.ing.iac.es/Astronomy/instruments/signal/help.html
    http://www.ing.iac.es/Astronomy/instruments/signal/signal_code.html
    which in turn is an approximation (<5% error) to the numerical simulation
    from the `light_in_slit` code (http://www.ing.iac.es/~crb/misc/lightinslit.f)
    Assuming a Gaussian/Normal distribution and ignoring differential refraction,
    this can also be calculated analytically as:
        Phi(n) - Phi(-n)
    where Phi(x) is the normal function cumulative distribution function (e.g.
    `scipy.stats.norm.cdf()`  and `n` is the slit width sigma/2 (since the
    distribution is symmetric about 0).
    """

    vign = 1.0

    if tic_params.get('imaging', False) is False:
        # Spectroscopy
        try:
            ratio = tic_params['slit_width'].to(u.arcsec) / tic_params['fwhm'].to(u.arcsec)
        except AttributeError:
            ratio = tic_params['slit_width'] / tic_params['fwhm']

        if ratio < 0.76:
            vign = 0.868*ratio
        if 0.76 <= ratio < 1.40:
            vign = 0.37+0.393*ratio
        if 1.40 <= ratio < 2.30:
            vign = 1.00-0.089*(2.3-ratio)
        if ratio >= 2.3:
            vign = 1.0

    return vign


def compute_fwhm_tel(tic_params):
    """Compute the diffraction-limited PSF FWHM for the telescope with diameter
    given by <tic_params['m1_diameter']> at observing wavelength <tic_params['wavelength']>
    """

    ang_res = (tic_params['wavelength'].to(u.m) / tic_params['m1_diameter'].to(u.m)) * u.radian
    fwhm_tel = 1.028 * ang_res
    fwhm_tel = fwhm_tel.to(u.arcsec)

    return fwhm_tel


def compute_fwhm(tic_params):
    """Compute the FWHM image quality (returned as an astropy Quantity in arcsec).
    This is the combination of the diffraction limit set by the telescope (a function
    of telescope diameter and wavelength) and that of the atmosphere (a function of the
    seeing, airmass and wavelength and the wavefront outerscale.
    Formulae from http://www.eso.org/observing/etc/doc/helpfors.html

    Values needed from the tic_params dictionary:
    seeing: seeing at zenith at 500 nm (as an astropy Quantity in arcsec),
    airmass: airmass of observation (1...X),
    wavelength: wavelength of observation (as an astropy Quantity, normally in nm but anything convertable to nm will work),
    m1_diameter: diameter of primary mirror (as an astropy Quantity, normally in meters but anything convertable to meters will work)
    """

    # L_0 is the wave-front outer-scale. We have adopted a value of L_0=46m (van den Ancker et al. 2016, Proc.SPIE, Volume 9910, 111). 
    L_0 = 46.0 * u.m

    fwhm_tel = compute_fwhm_tel(tic_params)
    fwhm_atm = tic_params['seeing'] * tic_params['airmass']**0.6
    fwhm_atm *= (tic_params['wavelength'].to(u.nm) / (500.0*u.nm))**-0.2
    f_kolb = (1.0/(1+300.0*tic_params['m1_diameter']/L_0))-1.0
    # Fried parameter
    r_0 = (0.1*(u.arcsec*u.m)) * tic_params['seeing']**-1.0 * ((tic_params['wavelength'].to(u.nm)/(500.0*u.nm))**1.2) * tic_params['airmass']**-0.6

    fwhm_atm *= sqrt(1.0 + f_kolb * 2.183 * ((r_0/L_0)**0.356))

    fwhm_iq = sqrt(fwhm_atm.value**2 + fwhm_tel.value**2)

    return fwhm_iq * u.arcsec


def instrument_throughput(tic_params):
    """Calculate the throughput of a spectrograph instrument, excluding
    telescope, atmosphere, grating and detector.
    This model assumes a number of air-glass interfaces (given by
    [num_ar_coatings]; defaults to 6) with AR coatings, a number of coated
    reflective surfaces (given by [num_inst_mirrors]; defaults to 4),
    transmission through prism (2 passes) and a CCD window.

    The reflectance vs wavelength data for the AR coating comes from
    http://intranet.lco.gtn/FLOYDS_Optical_Elements#AR_Coating
    That for the mirrors comes from:
    http://intranet.lco.gtn/FLOYDS_Optical_Elements#Reflective_Coating
    but both are typical of commercial broadband coatings.
    Fused quartz and fused silica data comes from:
    https://www.newport.com/n/optical-materials
    No variation with wavelength is assumed as this is typically very
    small (excluding the grating)."""

    # Transmission/Reflection values of optical elements
    ar_coating = 0.99
    # Fused silica (for the prism) and fused quartz (for the CCD window)
    # turn out to have the same transmission...
    ccd_window = 0.9
    mirror_coating = 0.9925

    # Air-glass interfaces: prism (2 sides), field flattener (4 sides)
    num_ar_coating = tic_params.get('num_ar_coatings', 6)
    throughput = ar_coating**num_ar_coating
    # Fused silica prism (two passes)
    throughput *= ccd_window**2
    # Fused quartz CCD window
    throughput *= ccd_window
    # Mirrors:  Collimator, Fold, Camera, Grating
    num_mirrors = tic_params.get('num_inst_mirrors', 4)
    throughput *= mirror_coating**num_mirrors

    return throughput


def compute_floyds_snr(mag_i, exp_time, tic_params, dbg=True, emulate_signal=False):
    """Compute the per-pixel SNR for FLOYDS based on the passed SDSS/PS-i'
    magnitude (mag_i) for the given exposure time <exp_time>.
    The parameters that are also needed are passed in the <tic_params> dictionary.
    Not included is the (negligible) dark current"""

    # imaging = tic_params.get('imaging', False)

    # Photons per second from the source
    m_0 = compute_photon_rate(mag_i, tic_params, emulate_signal)

    eff_area = calculate_effective_area(tic_params, dbg)
    signal = m_0 * (exp_time * u.s) * eff_area

    # Compute sky brightness in photons/A/s/cm^2/arcsec^2 from sky magnitude (assumed to be a mag/sq. arcsec)
    sky = compute_photon_rate(tic_params['sky_mag'], tic_params, emulate_signal)
    sky = sky * eff_area * (exp_time * u.s)
    if dbg:
        print('Object=', signal, 'Sky=', sky)
    if dbg:
        print(tic_params['pixel_scale'] , tic_params['wave_scale'], tic_params.get('slit_width', 1.0*u.arcsec))

    # Scale sky (in photons/A/sq.arcsec) to size of slit
    sky2 = sky * tic_params.get('slit_width', 1.0*u.arcsec) * tic_params['pixel_scale'] * tic_params['wave_scale']

    # Calculate size of seeing disk in pixels
    seeing = 2.0 * tic_params['fwhm'] / tic_params['pixel_scale']
    if dbg:
        print('Seeing=', seeing, 'Sky2=', sky2)

    # Calculate fraction of light entering slit
    vignette = slit_vignette(tic_params)
    if dbg:
        print("Slit loss fraction=", vignette)

    signal2 = signal * tic_params['wave_scale'] * vignette
    # Disperse signal across FWHM in spacial direction and determine peak counts in central pixel
    frac_in_single_pix = erf(sqrt(log(2))/seeing.value)
    peak_counts = signal2 / tic_params['gain'] * frac_in_single_pix
    if dbg:
        print('Object (photons/pixel-step-in-wavelength)=', signal2)
        print('Object (counts/pixel)=', peak_counts)
        print('Proportion of light in single central pixel =', frac_in_single_pix)

    noise = signal2.value + seeing.value*(sky2.value + tic_params.get('read_noise', 0.0)**2)
    noise = sqrt(noise)
    snr = signal2.value / noise
    if dbg:
        print('SNR/pixel=', snr)

    # Determine from peak counts if part of the spectrum will saturate
    if peak_counts.value > 55000:
        saturated = True
    else:
        saturated = False

    return snr, saturated


def default_dark_sky_mags():
    """Returns a dictionary of the baseline (darkest possible) sky magnitudes
    in each passband.
    The sky brightnesses are from SIGNAL V14.5 for UBVRI
    and Tonry et al. (2012) for grizw."""

    sky_mags = {'U': 22.0, 'B': 22.7, 'V' : 21.9, 'R' : 21.0, 'I' : 20.0, 'Z' : 18.8,
                'gp' : 21.9, 'rp' : 20.8, 'ip' : 19.8, 'zp' : 19.2, 'w' : 20.6}

    return sky_mags


def map_filter_to_wavelength(passband='ip'):
    """Maps the given [passband] (defaults to 'ip' for SDSS-i') to a wavelength
    which is returned as an AstroPy Quantity in angstroms"""

    filter_cwave = {'U': 3600, 'B': 4300, 'V' : 5500, 'R' : 6500, 'I' : 8200, 'Z' : 9500,
                    'gp' : 4810, 'rp' : 6170, 'ip' : 7520, 'zp' : 8660, 'w' : 6080}
    wavelength = filter_cwave.get(passband, filter_cwave['ip']) * u.angstrom

    return wavelength


def map_filter_to_bandwidth(passband='ip'):
    """Maps the given [passband] (defaults to 'ip' for SDSS-i') to a bandwidth
    which is returned as an AstroPy Quantity in angstroms"""

    filter_bwidth = {'U': 501.61, 'B': 952.75, 'V' : 839.79, 'R' : 1298.29, 'I' : 3155.25, 'Z' : 700,
                    'up' : 638.91, 'gp' : 1487.49, 'rp' : 1391.42, 'ip' : 1287.66, 'zp' : 1026.15, 'w' : 4409.79}
    bandwidth = filter_bwidth.get(passband, filter_bwidth['ip']) * u.angstrom

    return bandwidth


def map_filter_to_calfilter(passband='rp'):
    """Maps the given [passband] (defaults to 'rp' for SDSS-r') to a known
    calibrateable filter for calviacat"""

    filter_mapping = { 'g' : 'g',
                       'r' : 'r',
                       'i' : 'i',
                       'w' : 'r',
                       'clear' : 'r',
                       'zs' : 'z'
                     }
    return filter_mapping.get(passband.replace('p', ''), None)


def construct_tic_params(instrument, passband='ip'):
    """Builds and returns the dict of telescope, instrument & CCD parameters ("tic_params")
    for the specified <instrument> (one of {F65-FLOYDS, E10-FLOYDS}) and <passband>
    (defaults to 'ip' for SDSS-i')

    Filter central wavelengths, flux and sky brightnesses are from SIGNAL V14.5 for UBVRI
    and Tonry et al. (2012) for grizw. (Sky brightness is degraded by 0.2 mags for FTS)
    For FLOYDS:
        Instrument efficiencies are calculated from the optical prescription and elements
        Grating efficiency measured from printout of Richardson Gratings spec sheet (~5%)
        CCD QE measured from printout of Andor spec sheet (~2%)
        Readnoise and pixel size from Andor spec sheet
    """

    flux_janskys = {'U': 1810, 'B': 4260, 'V' : 3640, 'R' : 3080, 'I' : 2550, 'Z' : 2200,
                    'gp': 3631, 'rp': 3631, 'ip': 3631, 'zp': 3631, 'w' : 3631}
    sky_mags = default_dark_sky_mags()

    # CCD QE for Andor Newton 940-BU (values interpolated from printout of datasheet)
    ccd_qe_percent = {'U' : 76.0,  'B' : 92.5, 'V' : 84.0, 'R' : 79.0, 'I' : 57.0, 'Z' : 23.0,
                      'gp' : 90.0, 'rp' : 81.0, 'ip': 70.0, 'zp': 48.0, 'w' : 81.5}

    # Grating efficiency for Richardson Gratings 53-*-790R 235 lines/mm grating
    # (Values interpolated midway between S- and P-polarization curves)
    grating_eff_percent = {'U' :  2.6,  'B' : 15.5, 'V' : 60.0, 'R' : 84.0, 'I' : 87.5, 'Z' : 82.5,
                           'gp' : 33.5, 'rp' : 78.0, 'ip': 87.0, 'zp': 85.5, 'w' : 76.5}

    ft_area = 2.574*u.meter**2
    floyds_read_noise = 3.7
    tic_params = {}

    wavelength = map_filter_to_wavelength(passband)
    flux_mag0_Jy = flux_janskys.get(passband, flux_janskys['ip']) * u.Jy
    sky_mag = sky_mags.get(passband, sky_mags['ip'])
    ccd_qe = ccd_qe_percent.get(passband, ccd_qe_percent['ip'])
    ccd_qe /= 100.0
    grating_eff = grating_eff_percent.get(passband, grating_eff_percent['ip'])
    grating_eff /= 100.0

    if instrument.upper() == 'F65-FLOYDS':
        tic_params = {
                       'sky_mag'   : sky_mag,
                       'read_noise': floyds_read_noise,
                       'eff_area'  : ft_area,
                       'flux_mag0' : flux_mag0_Jy,
                       'wavelength':  wavelength,
                       'filter'    : passband,
                       'num_mirrors' : 3,  # M1, M2 plus Tertiary fold mirror
                       'num_ar_coatings' : 6,
                       'num_inst_mirrors' : 4,  # No. of reflective surfaces inside instrument
                       'grating_eff': grating_eff,
                       'ccd_qe'     : ccd_qe,
                       'pixel_scale': 24.96*(u.arcsec/u.mm)*(13.5*u.micron).to(u.mm)/u.pixel,
                       'wave_scale' : 3.51*(u.angstrom/u.pixel),
                       'fwhm' : 1.3 * u.arcsec,
                       'slit_width' : 6.0 * u.arcsec,
                       'gain'       : 2.0 * u.photon / u.count,
                     }
    elif instrument.upper() == 'E10-FLOYDS':
        tic_params = {
                       'sky_mag'   : sky_mag-0.2,
                       'read_noise': floyds_read_noise,
                       'eff_area'  : ft_area,
                       'flux_mag0' : flux_mag0_Jy,
                       'wavelength':  wavelength,
                       'filter'    : passband,
                       'num_mirrors' : 3,  # M1, M2 plus Tertiary fold mirror
                       'num_ar_coatings' : 6,
                       'num_inst_mirrors' : 4,  # No. of reflective surfaces inside instrument
                       'grating_eff': grating_eff,
                       'ccd_qe'     : ccd_qe,
                       'pixel_scale': 24.96*(u.arcsec/u.mm)*(13.5*u.micron).to(u.mm)/u.pixel,
                       'wave_scale' : 3.51*(u.angstrom/u.pixel),
                       'fwhm' : 1.7 * u.arcsec,
                       'slit_width' : 6.0 * u.arcsec,
                       'gain'       : 2.0 * u.photon / u.count,
                     }
    # Calculate and store instrument efficiency
    tic_params['instrument_eff'] = instrument_throughput(tic_params)

    return tic_params


def calc_asteroid_snr(mag, passband, exp_time, taxonomy='Mean', instrument='F65-FLOYDS', params={}, optimize=False, dbg=False):
    """Wrapper routine to calculate the SNR in <exp_time> seconds for an asteroid of
    magnitude <mag> in <passband> for the specific [taxonomy] (defaults to 'Mean' for S+C)
    and the specific instrument [instrument] (defaults to 'F65-FLOYDS'). Airmass defaults to 1.2
    if not specified in `[params['airmass']]`
    """

    desired_passband = 'V'
    new_mag = None
    new_passband = None
    snr = -99.0

    # If filter is not 'V', map to new passband
    if passband != desired_passband:
        new_mag = transform_Vmag(mag, desired_passband, taxonomy)
        if dbg:
            print("New object mag=", new_mag)
        new_passband = 'V'
    else:
        new_mag = mag
        new_passband = 'V'

    tic_params = construct_tic_params(instrument, new_passband)
    # Add default airmass
    tic_params['airmass'] = 1.2
    if dbg:
        print(tic_params)

    # Apply any overrides from passed params dictionary
    for key in params:
        if key == 'moon_phase':
            if dbg:
                print("Setting sky background. Was: ", tic_params['sky_mag'])
            tic_params['sky_mag'] = calc_sky_brightness(new_passband, params['moon_phase'])
            if dbg:
                print("Now:", tic_params['sky_mag'])
        elif key in tic_params.keys():
            if dbg:
                print("Setting %s to %s" % (key, params[key]))
            tic_params[key] = params[key]
    if not optimize:
        snr, saturated = compute_floyds_snr(new_mag, exp_time, tic_params, dbg)
        return new_mag, new_passband, snr, saturated
    else:
        op_exp_time = optimize_spectro_exp_time(new_mag, exp_time, tic_params, dbg)
        return op_exp_time


def optimize_spectro_exp_time(mag, exptime, tic_params, dbg=False):
    """Step through a series of exposure times, scaling each step based on the current exposure time,
    until we find the maximum exposure time that is unlikely to saturate any pixels in the detector.
    Return this exposure time.
    """
    snr, saturated = compute_floyds_snr(mag, exptime, tic_params, dbg)
    while saturated:
        if exptime > 100:
            exptime -= 10
        elif exptime > 10:
            exptime -= 5
        elif exptime > 1:
            exptime -= 1
        elif exptime > .1:
            exptime -= .1
        else:
            return 0.1
        snr, saturated = compute_floyds_snr(mag, exptime, tic_params, dbg)
        if dbg:
            print("New Exposure time:{}s, Saturation is {}".format(exptime, saturated))
    return exptime

def raw_aperture_photometry(sci_path, rms_path, mask_path, ra, dec,
                            aperture_radius=3*u.pixel, apply_calibration=False):
    """Perform raw (uncalibrated) aperture photometry on an image (along with its
    associated rms and mask images) at the locations specified by a set of positions
    given by <ra>, <dec>. Adapted from the zuds_pipeline, uses photutils.

    Parameters
    ----------
    sci_path : str
        Filepath for the science image to be photometered
    rms_path : str
        Filepath for the rms/weight image to be photometered
    mask_path : str
        Filepath for the mask image to be photometered. If not present or it
        can't be opened, an array of 1's of the same size as the science
        image is generated.
    ra : list or array-like of floats
        Right ascension of the sources to be measured (in degrees)
    dec : list or array-like of floats
        Declination of the sources to be measured (in degrees)
    aperture_radius : `astropy.units.Quantity` or `float`, optional
        Size of aperture radius in pixels (converted to arcsec using mean
        pixelscale from header WCS)

    Returns
    -------
    phot_table : `astropy.table.QTable` Table of photometric results from
        photutils augmented by additional columns:
        'id' : running number for each source (int)
        'xcenter' : x coordinate of the aperture center (pixels)
        'ycenter' : y coordinate of the apertur center (pixels)
        'sky_center' : RA, Dec of original input aperture coordinates (SkyCoord)
        'flux' : The sum of the values within the aperture (renamed from `aperture_sum`)
        'fluxerr' : The corresponding uncertainty in the 'flux' values (renamed from `aperture_sum_err`)
        'flags' : Flags
        'zp' : Zeropoint (extracted from the `L1ZP` value in the FITS header or 25.0 assumed)
        'obsmjd' : MJD of observation
        'filtercode' : Filter used
    """

    import photutils.aperture as aperture

    ra = np.atleast_1d(ra)
    dec = np.atleast_1d(dec)
    coord = SkyCoord(ra, dec, unit='deg')
    to_memmap = True # Originally False for ZTF but should be fine for LCO

    with fits.open(sci_path, memmap=to_memmap) as shdu:
        header = shdu[0].header
        swcs = WCS(header)
        scipix = shdu[0].data

        units = swcs.world_axis_units
        u1 = getattr(u, units[0])
        u2 = getattr(u, units[1])
        scales = proj_plane_pixel_scales(swcs)
        ps1 = (scales[0] * u1).to('arcsec').value
        ps2 = (scales[1] * u2).to('arcsec').value
        pixel_scale = np.mean(np.asarray([ps1, ps2])) * u.arcsec / u.pixel

    with fits.open(rms_path, memmap=to_memmap) as rhdu:
        rmspix = rhdu[0].data

    try:
        with fits.open(mask_path, memmap=to_memmap) as mhdu:
            maskpix = mhdu[0].data
    except FileNotFoundError:
        maskpix = np.ones_like(scipix)

    apertures = aperture.SkyCircularAperture(coord, r=aperture_radius*pixel_scale)
    phot_table = aperture.aperture_photometry(scipix, apertures,
                                               error=rmspix,
                                               wcs=swcs)


    pixap = apertures.to_pixel(swcs)
    annulus_masks = pixap.to_mask(method='center')
    maskpix = [annulus_mask.cutout(maskpix) for annulus_mask in annulus_masks]


    magzp = header.get('L1ZP', 25)
    apcor = header.get('APER_KEY', 0.0)

    # check for invalid photometry on masked pixels
    phot_table['flags'] = [np.bitwise_or.reduce(m.astype(int), axis=(0, 1)) for
                           m in maskpix]

    phot_table['zp'] = magzp + apcor
    phot_table['obsmjd'] = header['MJD-OBS']
    phot_table['filtercode'] = 'z' + header['L1FILTER'][-1]


    # rename some columns
    phot_table.rename_column('aperture_sum', 'flux')
    phot_table.rename_column('aperture_sum_err', 'fluxerr')

    return phot_table
