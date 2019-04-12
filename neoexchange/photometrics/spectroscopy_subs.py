import os

import numpy as np
from astropy import units as u
from synphot import units, SourceSpectrum, SpectralElement, specio
from synphot.spectrum import BaseUnitlessSpectrum, Empirical1D

from photometrics.photometry_subs import construct_tic_params, calculate_effective_area

def sptype_to_pickles_standard(sp_type):
    """Maps the passed <sp_type> e.g. 'F8V' to a Pickles standard star filename.
    None is returned if there is no match.
    References: http://www.stsci.edu/hst/observatory/crds/pickles_atlas.html
    Pickles (1998) (PASP 110, 863)"""

    # These are the main sequence dwarf, solar metallicity standards.
    mapping = { 'O5V' : 'pickles_1.fits',
                'O9V' : 'pickles_2.fits',
                'B0V' : 'pickles_3.fits',
                'B1V' : 'pickles_4.fits',
                'B3V' : 'pickles_5.fits',
                'B5V' : 'pickles_6.fits',
                'B6V' : 'pickles_6.fits',
                'B7V' : 'pickles_6.fits',
                'B8V' : 'pickles_7.fits',
                'B9V' : 'pickles_8.fits',
                'A0V' : 'pickles_9.fits',
                'A2V' : 'pickles_10.fits',
                'A3V' : 'pickles_11.fits',
                'A5V' : 'pickles_12.fits',
                'A7V' : 'pickles_13.fits',
                'F0V' : 'pickles_14.fits',
                'F2V' : 'pickles_15.fits',
                'F5V' : 'pickles_16.fits',
                'F6V' : 'pickles_18.fits',
                'F8V' : 'pickles_20.fits',
                'G0V' : 'pickles_23.fits',
                'G2V' : 'pickles_26.fits',
                'G5V' : 'pickles_27.fits',
                'G8V' : 'pickles_30.fits',
                'K0V' : 'pickles_31.fits',
                'K2V' : 'pickles_33.fits',
                'K3V' : 'pickles_34.fits',
                'K4V' : 'pickles_35.fits',
                'K5V' : 'pickles_36.fits',
                'K7V' : 'pickles_37.fits',
                'M0V' : 'pickles_38.fits',
                'M1V' : 'pickles_39.fits',
                'M2V' : 'pickles_40.fits',
                'M3V' : 'pickles_42.fits',
                'M4V' : 'pickles_43.fits',
                'M5V' : 'pickles_44.fits',
                'M6V' : 'pickles_45.fits'
            }

    return mapping.get(sp_type.upper(), None)

def get_filter_transmission(optics_path, filename='FLOYDS_AG_filter.csv'):
    header, wavelengths, trans = specio.read_ascii_spec(os.path.join(optics_path, filename), wave_unit=u.nm, flux_unit='%', delimiter=',', header_start=0, data_start=64)
    trans *= 100
    bp = SpectralElement(Empirical1D, points=wavelengths, lookup_table=trans)

    return bp

def get_mirror_reflectivity(optics_path):
    header, wavelengths, refl = specio.read_ascii_spec(os.path.join(optics_path, 'Protected_Al_mirror.dat'), wave_unit=u.nm, flux_unit='%')
    mirror = BaseUnitlessSpectrum(Empirical1D, points=wavelengths, lookup_table=refl)

    return mirror

def calculate_tel_throughput(optics_path, tic_params):

    mirror = get_mirror_reflectivity(optics_path)

    optics = mirror
    for x in range(0, tic_params['num_mirrors']-1):
        optics *= mirror
    return optics

def calculate_ag_throughput(optics_path, tic_params):
    header, wavelengths, trans = specio.read_ascii_spec(os.path.join(optics_path, 'FLOYDS_AG_lens.dat'), wave_unit=u.nm, flux_unit='%')
    lens = BaseUnitlessSpectrum(Empirical1D, points=wavelengths, lookup_table=trans)

    header, wavelengths, trans = specio.read_ascii_spec(os.path.join(optics_path, 'FLOYDS_AG_CCD_qe.dat'), wave_unit=u.nm, flux_unit='%')
    ccd = BaseUnitlessSpectrum(Empirical1D, points=wavelengths, lookup_table=trans)

    mirror = get_mirror_reflectivity(optics_path)

    ag_filter = get_filter_transmission(optics_path)

    throughput = mirror * lens * ag_filter * ccd

    return throughput

def calculate_inst_throughput(optics_path, tic_params):
    header, wavelengths, trans = specio.read_ascii_spec(os.path.join(optics_path, 'FLOYDS_AR_coating.dat'), wave_unit=u.nm, flux_unit='transmission')
    ar = BaseUnitlessSpectrum(Empirical1D, points=wavelengths, lookup_table=trans)
    ar/=100.0
    optics = ar
    for x in range(0, tic_params['num_ar_coatings']-1):
        optics *= ar

    header, wavelengths, trans = specio.read_ascii_spec(os.path.join(optics_path, 'FLOYDS_grating.dat'), wave_unit=u.nm, flux_unit='transmission')
    grating = BaseUnitlessSpectrum(Empirical1D, points=wavelengths, lookup_table=trans)
    grating/=100.

    header, wavelengths, trans = specio.read_ascii_spec(os.path.join(optics_path, 'FLOYDS_CCD_qe.dat'), wave_unit=u.nm, flux_unit='%')
    ccd = BaseUnitlessSpectrum(Empirical1D, points=wavelengths, lookup_table=trans)

    mirror = get_mirror_reflectivity(optics_path)
    inst_mirrors = mirror

    for x in range(0, tic_params['num_inst_mirrors']-1):
        inst_mirrors *= mirror

    throughput = optics * 0.9**2 * 0.9 * inst_mirrors * grating * ccd

    return throughput

def sun_and_sky(sun_file, sky_file):
    sun = SourceSpectrum.from_file(sun_file)
    sky = SpectralElement.from_file(sky_file, wave_col='lam', flux_col='trans', wave_unit=u.micron,flux_unit=u.dimensionless_unscaled)

    solar_plus_atmos = sun * sky

    return solar_plus_atmos

def synthesize_solar_standard(V_mag, sun_file, sky_file, tic_params, optics_path):

    solar_standard = sun_and_sky(sun_file, sky_file)
    flux_factor = 10.0**(-0.4*(V_mag - -26.7))
    solar_standard *= flux_factor

    inst_throughput = calculate_inst_throughput(optics_path, tic_params)
    tel_throughput = calculate_tel_throughput(optics_path, tic_params)
    solar_standard *= tel_throughput * inst_throughput

    return solar_standard

def synthesize_asteroid(V_mag, ast_file, sun_file, sky_file, tic_params, optics_path):

    solar_standard = sun_and_sky(sun_file, sky_file)

    header, wavelengths, reflect = specio.read_ascii_spec(ast_file, wave_unit=units.u.micron,flux_unit=units.u.dimensionless_unscaled)
    asteroid = BaseUnitlessSpectrum(Empirical1D, points=wavelengths, lookup_table=reflect)

    asteroid_spectrum = solar_standard * asteroid
    flux_factor = 10.0**(-0.4*(V_mag - -26.7))
    asteroid_spectrum *= flux_factor

    inst_throughput = calculate_inst_throughput(optics_path, tic_params)
    tel_throughput = calculate_tel_throughput(optics_path, tic_params)
    asteroid_spectrum *= tel_throughput * inst_throughput

    return asteroid_spectrum

def region_around_line(w, flux, cont):
    """cut out and normalize flux around a line

    Parameters
    ----------
    w : 1 dim np.ndarray
        array of wavelengths
    flux : 1 dim np.ndarray
        array of flux values
    cont : list of lists
        wavelengths for continuum normalization [[low1,up1],[low2, up2]]
        that described two areas on both sides of the line
    """

    #index is true in the region where we fit the polynomial
    indcont = ((w > cont[0][0]) & (w < cont[0][1])) |((w > cont[1][0]) & (w < cont[1][1]))
    #index of the region we want to return
    indrange = (w > cont[0][0]) & (w < cont[1][1])
    # make a flux array of shape
    # (number of spectra, number of points in indrange)
    f = np.zeros(indrange.sum())
    # fit polynomial of second order to the continuum region
    linecoeff = np.polyfit(w[indcont], flux[indcont],2)
    # divide the flux by the polynomial and put the result in our
    # new flux array
    f = flux[indrange]/np.polyval(linecoeff, w[indrange])

    return w[indrange], f

if __name__ == 'main':
    cdbs = os.getenv('CDBS_PATH', os.path.join(os.path.sep,'apophis','tlister','cdbs'))
    calspec = os.path.join(cdbs, 'calspec')
    sun_file = os.path.join(calspec, 'sun_reference_stis_002.fits')
    sky_file = os.path.join(cdbs,'extinction','skytable_z1.2_pwv3.5_new_moon.fits')
    tic_params = construct_tic_params('F65-FLOYDS')
    optics_path = os.getenv('OPTICS_PATH', os.path.join('photometrics', 'data'))
    solar_analog = synthesize_solar_standard(10.57, sun_file, sky_file, tic_params, optics_path)
    solar_analog.plot(left=3000, right=11000, flux_unit=units.FLAM, save_as='solar_standard.png')
