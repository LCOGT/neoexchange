import os

from astropy import units as u
from synphot import units, SourceSpectrum, SpectralElement, specio
from synphot.spectrum import BaseUnitlessSpectrum, Empirical1D

from photometrics.photometry_subs import construct_tic_params, calculate_effective_area

def calculate_tel_throughput(optics_path, tic_params):
    header, wavelengths, refl = specio.read_ascii_spec(os.path.join(optics_path, 'subaru_m1_r_20171023.txt'), wave_unit=u.nm, flux_unit='%', delimiter='\t')
    mirror = BaseUnitlessSpectrum(Empirical1D, points=wavelengths, lookup_table=refl)
    optics = mirror
    for x in range(0, tic_params['num_mirrors']-1):
        optics *= mirror
    return optics

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
    throughput = optics*0.9**2*0.9*0.9925**tic_params['num_inst_mirrors']*grating*ccd

    return throughput

def synthesize_solar_standard(V_mag, sun_file, sky_file, tic_params, optics_path):
    sun = SourceSpectrum.from_file(sun_file)
    sky = SpectralElement.from_file(sky_file, wave_col='lam', flux_col='trans', wave_unit=u.micron,flux_unit=u.dimensionless_unscaled)

    flux_factor = 10.0**(-0.4*(V_mag - -26.7))
    solar_standard = sun * flux_factor
    solar_standard *= sky

    inst_throughput = calculate_inst_throughput(optics_path, tic_params)
    tel_throughput = calculate_tel_throughput(optics_path, tic_params)
    solar_standard *= tel_throughput * inst_throughput

    return solar_standard

if __name__ == 'main':
    cdbs = os.getenv('CDBS_PATH', os.path.join(os.path.sep,'data','tlister','cdbs'))
    calspec = os.path.join(cdbs, 'calspec')
    sun_file = os.path.join(calspec, 'sun_reference_stis_002.fits')
    sky_file = os.path.join(cdbs,'extinction','skytable_z1.2_pwv3.5_new_moon.fits')
    tic_params = construct_tic_params('F65-FLOYDS')
    optics_path = os.getenv('OPTICS_PATH', os.path.join(os.getenv('HOME'), 'Dropbox', 'Asteroids'))
    solar_analog = synthesize_solar_standard(10.57, sun_file, sky_file, tic_params, optics_path)
    solar_analog.plot(left=3000, right=11000, flux_unit=units.FLAM, save_as='solar_standard.png')
