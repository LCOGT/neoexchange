import os

from astropy import units as u
from synphot import units, SourceSpectrum, SpectralElement
from synphot.spectrum import BaseUnitlessSpectrum

from photometrics.photometry_subs import construct_tic_params, calculate_effective_area


def synthesize_solar_standard(V_mag, sun_file, sky_file, tic_params):
    sun = SourceSpectrum.from_file(sun_file)
    sky = SpectralElement.from_file(sky_file, wave_col='lam', flux_col='trans', wave_unit=u.micron,flux_unit=u.dimensionless_unscaled)

    flux_factor = 10.0**(-0.4*(V_mag - -26.7))
    solar_standard = sun * flux_factor
    solar_standard *= sky
    tic_params['extinction'] = 0.0
    tic_params['eff_area'] = 1.0 * (u.cm**2)
    throughput = calculate_effective_area(tic_params)
    throughput = throughput.value
    solar_standard *= throughput

    return solar_standard

if __name__ == 'main':
    cdbs = os.getenv('CDBS_PATH', os.path.join(os.path.sep,'data','tlister','cdbs'))
    calspec = os.path.join(cdbs, 'calspec')
    sun_file = os.path.join(calspec, 'sun_reference_stis_002.fits')
    sky_file = os.path.join(cdbs,'extinction','skytable_z1.2_pwv3.5_new_moon.fits')
    tic_params = construct_tic_params('F65-FLOYDS')
    solar_analog = synthesize_solar_standard(10.0, sun_file, sky_file, tic_params)
    solar_analog.plot(left=3000, right=11000, flux_unit=units.FLAM)
