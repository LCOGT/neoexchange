'''
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2017-2017 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''

from math import acos
from django.test import TestCase
from astropy import units as u

#Import module to test
from photometrics.photometry_subs import *

class TestTransformVmag(TestCase):

    def test_taxon_default_to_i(self):

        V = 20.0
        new_passband = 'i'

        expected_mag = V-0.39

        new_mag = transform_Vmag(V, new_passband)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_mean_to_i(self):

        V = 20.0
        new_passband = 'i'
        taxonomy = 'Mean'

        expected_mag = V-0.39

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_mean_uppercase_to_i(self):

        V = 20.0
        new_passband = 'i'
        taxonomy = 'MEAN'

        expected_mag = V-0.39

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_mean_lowercase_to_i(self):

        V = 20.0
        new_passband = 'i'
        taxonomy = 'mean'

        expected_mag = V-0.39

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_bad(self):

        V = 20.0
        new_passband = 'i'
        taxonomy = 'foo'

        expected_mag = None

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_bad_passband(self):

        V = 20.0
        new_passband = 'U'
        taxonomy = 'mean'

        expected_mag = None

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_bad_uc_passband(self):

        V = 20.0
        new_passband = 'R'  # Bessell-R not the same as (SDSS/PS)-r
        taxonomy = 'mean'

        expected_mag = None

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_solar_to_i(self):

        V = 20.5
        new_passband = 'i'
        taxonomy = 'Solar'

        expected_mag = V-0.293

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_mean_to_w(self):

        V = 19.0
        new_passband = 'w'
        taxonomy = 'Mean'

        expected_mag = V-0.16

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_solar_to_w(self):

        V = 16.25
        new_passband = 'w'
        taxonomy = 'Solar'

        expected_mag = V-0.114

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_mean_to_r(self):

        V = 19.1
        new_passband = 'r'
        taxonomy = 'MeAn'

        expected_mag = V-0.23

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_solar_to_r(self):

        V = 16.25
        new_passband = 'r'
        taxonomy = 'solaR'

        expected_mag = V-0.183

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_Stype_to_r(self):

        V = 10
        new_passband = 'r'
        taxonomy = 'S'

        expected_mag = V-0.275

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_Stype_to_i(self):

        V = 10
        new_passband = 'i'
        taxonomy = 'S'

        expected_mag = V-0.470

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_Stype_to_w(self):

        V = 10
        new_passband = 'w'
        taxonomy = 'S'

        expected_mag = V-0.199

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_Ctype_to_r(self):

        V = 10
        new_passband = 'r'
        taxonomy = 'C'

        expected_mag = V-0.194

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_Ctype_to_i(self):

        V = 10
        new_passband = 'i'
        taxonomy = 'c'

        expected_mag = V-0.308

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_Ctype_to_w(self):

        V = 10
        new_passband = 'w'
        taxonomy = 'C'

        expected_mag = V-0.120

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_Xtype_to_r(self):

        V = 10
        new_passband = 'r'
        taxonomy = 'X'

        expected_mag = V-0.207

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_Xtype_to_i(self):

        V = 10
        new_passband = 'i'
        taxonomy = 'x'

        expected_mag = V-0.367

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_Xtype_to_w(self):

        V = 10
        new_passband = 'w'
        taxonomy = 'X'

        expected_mag = V-0.146

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_Qtype_to_r(self):

        V = 15.1
        new_passband = 'r'
        taxonomy = 'Q'

        expected_mag = V-0.252

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_Qtype_to_i(self):

        V = 12.5
        new_passband = 'i'
        taxonomy = 'q'

        expected_mag = V-0.379

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_Qtype_to_w(self):

        V = 14
        new_passband = 'w'
        taxonomy = 'Q'

        expected_mag = V-0.156

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_NEOtype_to_r(self):

        V = 15.1
        new_passband = 'r'
        taxonomy = 'NeO'

        expected_mag = V-0.213

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_NEOtype_to_i(self):

        V = 12.5
        new_passband = 'i'
        taxonomy = 'neo'

        expected_mag = V-0.356

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_NEOtype_to_w(self):

        V = 14
        new_passband = 'w'
        taxonomy = 'NEO'

        expected_mag = V-0.148

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)


class TestSkyBrightness(TestCase):

    def setUp(self):
        self.dark_sky_mags = { 'U': 22.0, 'B': 22.7, 'V' : 21.9, 'R' : 21.0, 'I' : 20.0, 'Z' : 18.8,
                    'gp' : 21.9, 'rp' : 20.8, 'ip' : 19.8, 'zp' : 19.2, 'w' : 20.6 }

        self.precision = 4

    def test_V_dark(self):
        expected_mag = self.dark_sky_mags['V']-0.4

        sky_mag = calc_sky_brightness('V', 'D')

        self.assertAlmostEqual(expected_mag, sky_mag, self.precision)

    def test_V_gray(self):
        expected_mag = self.dark_sky_mags['V']-2.15

        sky_mag = calc_sky_brightness('V', 'G')

        self.assertAlmostEqual(expected_mag, sky_mag, self.precision)

    def test_V_bright(self):
        expected_mag = self.dark_sky_mags['V']-3.4

        sky_mag = calc_sky_brightness('V', 'B')

        self.assertAlmostEqual(expected_mag, sky_mag, self.precision)

    def test_B_dark(self):
        expected_mag = self.dark_sky_mags['B']-0.4

        sky_mag = calc_sky_brightness('B', 'D')

        self.assertAlmostEqual(expected_mag, sky_mag, self.precision)

    def test_B_gray(self):
        expected_mag = self.dark_sky_mags['B']-2.15

        sky_mag = calc_sky_brightness('B', 'G')

        self.assertAlmostEqual(expected_mag, sky_mag, self.precision)

    def test_B_bright(self):
        expected_mag = self.dark_sky_mags['B']-3.4

        sky_mag = calc_sky_brightness('B', 'B')

        self.assertAlmostEqual(expected_mag, sky_mag, self.precision)

    def test_R_dark(self):
        expected_mag = 20.6

        sky_mag = calc_sky_brightness('R', 'D')

        self.assertAlmostEqual(expected_mag, sky_mag, self.precision)

    def test_R_gray(self):
        expected_mag = 19.7

        sky_mag = calc_sky_brightness('R', 'G')

        self.assertAlmostEqual(expected_mag, sky_mag, self.precision)

    def test_R_bright(self):
        expected_mag = 18.3

        sky_mag = calc_sky_brightness('R', 'B')

        self.assertAlmostEqual(expected_mag, sky_mag, self.precision)

    def test_ip_dark(self):
        expected_mag = 19.4

        sky_mag = calc_sky_brightness('ip', 'D')

        self.assertAlmostEqual(expected_mag, sky_mag, self.precision)

    def test_ip_gray(self):
        expected_mag = 18.5

        sky_mag = calc_sky_brightness('ip', 'G')

        self.assertAlmostEqual(expected_mag, sky_mag, self.precision)

    def test_ip_bright(self):
        expected_mag = 17.1

        sky_mag = calc_sky_brightness('ip', 'B')

        self.assertAlmostEqual(expected_mag, sky_mag, self.precision)

class TestSkyBrightnessModel(TestCase):

    def setUp(self):
        self.params = { 'bandpass': 'V',
                        'moon_phase_angle': 171.0,
                        'moon_target_sep': 60.0,
                        'moon_zd': 80.0,
                        'target_zd': 42.7}
        self.precision = 3

    def test_l_sfu_h_elat_h_glat_new_moon(self):

        expected_sky_mag = 21.7556267

        self.params['sfu'] = 0.8 * u.MJy
        self.params['moon_zd'] = 110.0
        self.params['moon_target_sep'] = 120

        sky_mag = sky_brightness_model(self.params)

        self.assertAlmostEqual(expected_sky_mag, sky_mag, self.precision)

    def test_l_sfu_l_elat_h_glat_new_moon(self):

        expected_sky_mag = 21.5128479

        self.params['sfu'] = 0.8 * u.MJy
        self.params['moon_zd'] = 110.0
        self.params['moon_target_sep'] = 120
        self.params['ecliptic_lat'] = 10.0

        sky_mag = sky_brightness_model(self.params)

    def test_l_sfu_l_elat_h_glat_new_moon2(self):

        expected_sky_mag = 21.5128479

        self.params['sfu'] = 0.8 * u.MJy
        self.params['moon_zd'] = 110.0
        self.params['moon_target_sep'] = 120
        self.params['ecliptic_lat'] = 10.0 * u.deg

        sky_mag = sky_brightness_model(self.params)

    def test_l_sfu_l_elat_l_glat_new_moon(self):

        expected_sky_mag = 21.4401169

        self.params['sfu'] = 0.8 * u.MJy
        self.params['moon_zd'] = 110.0
        self.params['moon_target_sep'] = 120
        self.params['ecliptic_lat'] = 10.0
        self.params['galactic_lat'] = 15.0

        sky_mag = sky_brightness_model(self.params)

    def test_l_sfu_l_elat_l_glat_new_moon2(self):

        expected_sky_mag = 21.4401169

        self.params['sfu'] = 0.8 * u.MJy
        self.params['moon_zd'] = 110.0
        self.params['moon_target_sep'] = 120
        self.params['ecliptic_lat'] = 10.0 * u.deg
        self.params['galactic_lat'] = 15.0 * u.deg

        sky_mag = sky_brightness_model(self.params)

    def test_l_sfu_l_elat_l_glat_1stqtr_moon(self):

        expected_sky_mag = 20.6140327

        self.params['sfu'] = 0.8 * u.MJy
        self.params['moon_zd'] = 60
        self.params['moon_phase_angle'] = 90.0
        self.params['moon_target_sep'] = 120
        self.params['ecliptic_lat'] = 10.0
        self.params['galactic_lat'] = 15.0

        sky_mag = sky_brightness_model(self.params)

    def test_l_sfu_l_elat_l_glat_full_moon_far(self):

        expected_sky_mag = 18.8442268

        self.params['sfu'] = 0.8 * u.MJy
        self.params['moon_zd'] = 60
        self.params['moon_phase_angle'] = 10.0
        self.params['moon_target_sep'] = 120
        self.params['ecliptic_lat'] = 10.0
        self.params['galactic_lat'] = 15.0

        sky_mag = sky_brightness_model(self.params)

    def test_l_sfu_l_elat_l_glat_full_moon_near(self):

        expected_sky_mag = 18.2975235

        self.params['sfu'] = 0.8 * u.MJy
        self.params['moon_zd'] = 60
        self.params['moon_phase_angle'] = 10.0
        self.params['moon_target_sep'] = 40
        self.params['ecliptic_lat'] = 10.0
        self.params['galactic_lat'] = 15.0

        sky_mag = sky_brightness_model(self.params)

class TestComputeMoonBrightness(TestCase):

    def setUp(self):
        self.params = { 'bandpass': 'V',
                        'moon_phase_angle': 171.0,
                        'moon_target_sep': 60.0,
                        'moon_zd': 80.0,
                        'target_zd': 42.7}
        self.precision = 3

    def test_newmoon_low(self):
        expected_bkgd = 2.71436524

        moon_bkgd = compute_moon_brightness(self.params)

        self.assertAlmostEqual(expected_bkgd, moon_bkgd, self.precision)

    def test_newmoon_low_with_fli(self):
        expected_bkgd = 2.71436524

        alpha = 180.0-self.params['moon_phase_angle']
        fli = (1.0 - cos(radians(alpha)))/2.0
        self.assertAlmostEqual(0.0061558297024311703, fli, 7)
        self.params['moon_phase'] = fli
        del(self.params['moon_phase_angle'])
        moon_bkgd = compute_moon_brightness(self.params)

        self.assertAlmostEqual(expected_bkgd, moon_bkgd, self.precision)

    def test_1stqtrmoon_low(self):
        expected_bkgd = 346.073914

        self.params['moon_phase_angle'] = 90

        moon_bkgd = compute_moon_brightness(self.params)

        self.assertAlmostEqual(expected_bkgd, moon_bkgd, self.precision)

    def test_1stqtrmoon_high(self):
        expected_bkgd = 505.812622

        self.params['moon_phase_angle'] = 90
        self.params['moon_zd'] = 20.0

        moon_bkgd = compute_moon_brightness(self.params)

        self.assertAlmostEqual(expected_bkgd, moon_bkgd, self.precision)

    def test_fullmoon_high(self):
        expected_bkgd = 5558.60344

        self.params['moon_phase_angle'] = 0.0
        self.params['moon_zd'] = 20.0

        moon_bkgd = compute_moon_brightness(self.params)

        self.assertAlmostEqual(expected_bkgd, moon_bkgd, self.precision)

class SNRTestCase(TestCase):
    def __init__(self, *args, **kwargs):
        super(SNRTestCase, self).__init__(*args, **kwargs)

    def setUp(self):

        self.precision = 4
        self.expected_units = u.Unit('ph/(s*cm**2*AA)')

        self.ftn_tic_params = { 
                                'sky_mag'   : 19.8,
                                'read_noise': 3.7,
                                'eff_area'  : 2.84*u.meter**2,
                                'flux_mag0' : 3631.0*u.Jy,
                                'wavelength': 752.0*u.nm,
                                'filter'    : 'ip',
                                'num_mirrors' : 3,  # Tertiary fold mirror
                                'instrument_eff' : 0.42,
                                'grating_eff': 0.60,
                                'ccd_qe'     : 0.70,
                                'pixel_scale': 24.96*(u.arcsec/u.mm)*(13.5*u.micron).to(u.mm)/u.pixel,
                                'wave_scale' : 3.51*(u.angstrom/u.pixel),
                                'fwhm' : 1.0 * u.arcsec,
                                'slit_width' : 2.0 * u.arcsec,
                              }
        self.wht_tic_params = { 
                                'sky_mag'   : 20.0,
                                'read_noise': 3.9,
                                'eff_area'  : 12.47*u.meter**2,
                                'flux_mag0' : 2550.0*u.Jy,
                                'wavelength': 820.0*u.nm,
                                'filter'    : 'I',
                                'instrument_eff' : 0.42,
                                'grating_eff' : 0.60,
                                'ccd_qe'    : 0.80,
                                'pixel_scale' : 14.9*(u.arcsec/u.mm)*(15*u.micron).to(u.mm)/u.pixel,
                                'wave_scale' : 121.0*(u.angstrom/u.mm)*(15*u.micron).to(u.mm)/u.pixel,
                                'fwhm' : 1.0 * u.arcsec,
                                'slit_width' : 3.0 * u.arcsec,
                              }

class TestComputePhotonRate(SNRTestCase):

    def test_I_mag0(self):

        mag_I = 0.0
        expected_rate = 469.321344
        rate = compute_photon_rate(mag_I, self.wht_tic_params)

        self.assertAlmostEqual(expected_rate, rate.to_value(), self.precision)
        self.assertEqual(self.expected_units, rate.unit)

    def test_ip_mag0(self):

        mag_ip = 0.0
        expected_rate = 728.706068
        rate = compute_photon_rate(mag_ip, self.ftn_tic_params)

        self.assertAlmostEqual(expected_rate, rate.to_value(), self.precision)
        self.assertEqual(self.expected_units, rate.unit)

    def test_I_mag0_signal(self):

        mag_I = 0.0
        expected_rate = 471.1752
        rate = compute_photon_rate(mag_I, self.wht_tic_params, emulate_signal=True)

        self.assertAlmostEqual(expected_rate, rate.to_value(), self.precision)
        self.assertEqual(self.expected_units, rate.unit)

    def test_SDSS_ip_mag0_signal(self):

        mag_ip = 0.0
        expected_rate = 731.5845
        rate = compute_photon_rate(mag_ip, self.ftn_tic_params, emulate_signal=True)

        self.assertAlmostEqual(expected_rate, rate.to_value(), self.precision)
        self.assertEqual(self.expected_units, rate.unit)

    def test_I_mag18_signal(self):

        mag_I = 18.0
        expected_rate = 2.972914340482041e-05
        rate = compute_photon_rate(mag_I, self.wht_tic_params, emulate_signal=True)

        self.assertAlmostEqual(expected_rate, rate.to_value(), self.precision)
        self.assertEqual(self.expected_units, rate.unit)

    def test_SDSS_ip_mag18_signal(self):

        mag_ip = 18.0
        expected_rate = 4.6159855659670969e-05
        rate = compute_photon_rate(mag_ip, self.ftn_tic_params, emulate_signal=True)

        self.assertAlmostEqual(expected_rate, rate.to_value(), self.precision)
        self.assertEqual(self.expected_units, rate.unit)

    def test_V_mag0_signal(self):
        self.ftn_tic_params['flux_mag0'] = 3640.0*u.Jy
        self.ftn_tic_params['wavelength'] = 0.55*u.micron

        mag_V = 0.0
        expected_rate = 1002.75482
        rate = compute_photon_rate(mag_V, self.ftn_tic_params, emulate_signal=True)

        self.assertAlmostEqual(expected_rate, rate.to_value(), self.precision)
        self.assertEqual(self.expected_units, rate.unit)

    def test_V_mag0_microns(self):
        self.ftn_tic_params['flux_mag0'] = 3640.0*u.Jy
        self.ftn_tic_params['wavelength'] = 0.55*u.micron

        mag_V = 0.0
        expected_rate = 998.80951728995279
        rate = compute_photon_rate(mag_V, self.ftn_tic_params)

        self.assertAlmostEqual(expected_rate, rate.to_value(), self.precision)
        self.assertEqual(self.expected_units, rate.unit)

class TestExtinctionInBand(SNRTestCase):

    def test_I(self):

        expected_k = 0.06

        k = extinction_in_band(self.wht_tic_params)

        self.assertEqual(expected_k, k)

    def test_ip(self):

        expected_k = 0.075

        k = extinction_in_band(self.ftn_tic_params)

        self.assertEqual(expected_k, k)

    def test_I_override(self):

        expected_k = 0.01
        self.wht_tic_params['extinction'] = 0.01

        k = extinction_in_band(self.wht_tic_params)

        self.assertEqual(expected_k, k)

    def test_ip_override(self):

        expected_k = 0.082
        self.ftn_tic_params['extinction'] = 0.082

        k = extinction_in_band(self.ftn_tic_params)

        self.assertEqual(expected_k, k)

    def test_bad_filter(self):

        expected_k = 0.00
        self.ftn_tic_params['filter'] = 'foo'

        k = extinction_in_band(self.ftn_tic_params)

        self.assertEqual(expected_k, k)

    def test_bad_override_good_filter(self):

        expected_k = 0.075
        self.ftn_tic_params['extinction'] = 'foo'

        k = extinction_in_band(self.ftn_tic_params)

        self.assertEqual(expected_k, k)

    def test_bad_override_bad_filter(self):

        expected_k = 0.00
        self.ftn_tic_params['extinction'] = 'foo'
        self.ftn_tic_params['filter'] = 'foo'

        k = extinction_in_band(self.ftn_tic_params)

        self.assertEqual(expected_k, k)

class TestCalcEffectiveArea(SNRTestCase):

    def test_wht_I(self):

        expected_area = 17186.794281005859 * u.cm**2

        area = calculate_effective_area(self.wht_tic_params)

        self.assertAlmostEqual(expected_area.to_value(u.m**2), area.to_value(u.m**2), 6)
        self.assertEqual(expected_area.unit, area.unit)

    def test_ftn_I(self):

        expected_area = 3327.098429203033 * u.cm**2
# Override values to match SIGNAL
        self.ftn_tic_params['extinction'] = 0.06
        self.ftn_tic_params['ccd_qe'] = 0.80

        area = calculate_effective_area(self.ftn_tic_params)

        self.assertAlmostEqual(expected_area.to_value(u.m**2), area.to_value(u.m**2), 6)
        self.assertEqual(expected_area.unit, area.unit)

    def test_ftn_I_2(self):

        expected_area = 2328.969091176987 * u.cm**2
# Override values to match SIGNAL
        self.ftn_tic_params['extinction'] = 0.06
        self.ftn_tic_params['ccd_qe'] = 0.56

        area = calculate_effective_area(self.ftn_tic_params)

        self.assertAlmostEqual(expected_area.to_value(u.m**2), area.to_value(u.m**2), 6)
        self.assertEqual(expected_area.unit, area.unit)

class TestFloydsThroughput(SNRTestCase):

    def test1(self):
        expected_throughput = 0.6437800300612727

        tic_params = {'grating_eff' : 0.87}

        throughput = floyds_throughput(tic_params)

        self.assertEqual(expected_throughput, throughput)

class TestComputeFloydsSNR(SNRTestCase):


    def test_wht_I_signal(self):

# Setup to replicate value in SIGNAL:
# I Instrument = WHT ISIS
# E Extinction per airmass (mag)   0.00
# G Grating                     R158R
# D Detector                     RED+
# B Band I  = wavelength (A)    8200
# M Apparent magnitude            18.0
# T Integration time (sec)       100.0
# F FWHM (object*seeing, arcsec)   1.0
# K Sky brightness mag/sq.arcsec  20.00
# S Slit width (arcsec)            3.0
# A Airmass                        1.0
# (rest at defaults)

       mag_I = 18.0
       exp_time = 100.0
       # Override extinction
       self.wht_tic_params['extinction'] = 0.0

       expected_snr = 5.41718245

       snr = compute_floyds_snr(mag_I, exp_time, self.wht_tic_params, emulate_signal=True)

       self.assertAlmostEqual(expected_snr, snr, self.precision)

    def test_faint_ftn1(self):

        mag_i = 18.0
        exp_time = 100.0
        # Override defaults
        self.ftn_tic_params['slit_width'] = 3.0 * u.arcsec
        self.ftn_tic_params['grating_eff']= 0.87

        expected_snr = 4.47669678294

        snr =  compute_floyds_snr(mag_i, exp_time, self.ftn_tic_params)

        self.assertAlmostEqual(expected_snr, snr, self.precision)

    def test_signal_ftn_I(self):

        mag_I = 15.5
        exp_time = 100.0
        # Override defaults
        self.ftn_tic_params['flux_mag0']  = 2550.0*u.Jy
        self.ftn_tic_params['wavelength'] = 820.0*u.nm
        self.ftn_tic_params['sky_mag']    = 19.6
        self.ftn_tic_params['filter']     = 'I'
        self.ftn_tic_params['ccd_qe']     = 0.56
        self.ftn_tic_params['slit_width'] = 3.0 * u.arcsec

        expected_snr = 12.84996700

        snr =  compute_floyds_snr(mag_I, exp_time, self.ftn_tic_params, emulate_signal=True)

        self.assertAlmostEqual(expected_snr, snr, self.precision)

    def test_signal_ftn_ip(self):

        mag_I = 15.5
        exp_time = 100.0
        # Override defaults
        self.ftn_tic_params['slit_width'] = 3.0 * u.arcsec
        self.ftn_tic_params['grating_eff']= 0.87

        expected_snr = 23.37279701

        snr =  compute_floyds_snr(mag_I, exp_time, self.ftn_tic_params, emulate_signal=True)

        self.assertAlmostEqual(expected_snr, snr, self.precision)

    def test_signal_ftn_ip_bad_seeing(self):

        mag_I = 15.5
        exp_time = 100.0
        # Override defaults
        self.ftn_tic_params['slit_width'] = 2.0 * u.arcsec
        self.ftn_tic_params['fwhm']       = 1.6 * u.arcsec
        self.ftn_tic_params['grating_eff']= 0.87

        expected_snr = 20.62739182

        snr =  compute_floyds_snr(mag_I, exp_time, self.ftn_tic_params, emulate_signal=True)

        self.assertAlmostEqual(expected_snr, snr, self.precision)

class TestSlitVignette(SNRTestCase):

    def __init__(self, *args, **kwargs):
        self.precision = 7
        super(SNRTestCase, self).__init__(*args, **kwargs)

    def test_imaging(self):

        self.wht_tic_params['imaging'] = True

        expected_vign = 1.0

        vign = slit_vignette(self.wht_tic_params)

        self.assertAlmostEqual(expected_vign, vign, self.precision)

    def test_fwhm2_slit1(self):

        self.wht_tic_params['fwhm'] = 2.0
        self.wht_tic_params['slit_width'] = 1.0

        expected_vign = 0.434

        vign = slit_vignette(self.wht_tic_params)

        self.assertAlmostEqual(expected_vign, vign, self.precision)

    def test_fwhm1_slit1(self):

        self.wht_tic_params['fwhm'] = 1.0
        self.wht_tic_params['slit_width'] = 1.0

        expected_vign = 0.763

        vign = slit_vignette(self.wht_tic_params)

        self.assertAlmostEqual(expected_vign, vign, self.precision)

    def test_fwhm1_slit2(self):

        self.wht_tic_params['fwhm'] = 1.0
        self.wht_tic_params['slit_width'] = 2.00

        expected_vign = 0.9733

        vign = slit_vignette(self.wht_tic_params)

        self.assertAlmostEqual(expected_vign, vign, self.precision)

    def test_fwhm1pt6_slit2(self):

        self.wht_tic_params['fwhm'] = 1.6 * u.arcsec
        self.wht_tic_params['slit_width'] = 2.00 * u.arcsec

        expected_vign = 0.86125

        vign = slit_vignette(self.wht_tic_params)

        self.assertAlmostEqual(expected_vign, vign, self.precision)

    def test_fwhm1_slit2point31(self):

        self.wht_tic_params['fwhm'] = 1.0
        self.wht_tic_params['slit_width'] = 2.31

        expected_vign = 1.0

        vign = slit_vignette(self.wht_tic_params)

        self.assertAlmostEqual(expected_vign, vign, self.precision)

    def test_fwhm2pt0_slit1pt2(self):

        self.wht_tic_params['fwhm'] = 2.0 * u.arcsec
        self.wht_tic_params['slit_width'] = 1.20 * u.arcsec

        expected_vign = 0.5208

        vign = slit_vignette(self.wht_tic_params)

        self.assertAlmostEqual(expected_vign, vign, self.precision)

class TestCalcAsteroidSNR(SNRTestCase):

    def test_Vmag_default_taxon_FLOYDS(self):

        mag_V = 12.0
        passband = 'V'
        exp_time = 300
        spectrograph = 'F65-FLOYDS'

        expected_mag = mag_V - 0.39
        expected_passband = 'ip'
        expected_snr = 259.413444738

        mag, new_passband, snr = calc_asteroid_snr(mag_V, passband, exp_time, instrument=spectrograph)

        self.assertEqual(expected_mag, mag)
        self.assertEqual(expected_passband, new_passband)
        self.assertAlmostEqual(expected_snr, snr, self.precision)

    def test_Vmag_default_taxon_FTS_FLOYDS(self):

        mag_V = 12.0
        passband = 'V'
        exp_time = 300
        spectrograph = 'E10-FLOYDS'

        expected_mag = mag_V - 0.39
        expected_passband = 'ip'
        expected_snr = 244.7622302104532

        mag, new_passband, snr = calc_asteroid_snr(mag_V, passband, exp_time, instrument=spectrograph)

        self.assertEqual(expected_mag, mag)
        self.assertEqual(expected_passband, new_passband)
        self.assertAlmostEqual(expected_snr, snr, self.precision)

    def test_Vmag_default_taxon_FLOYDS_Gray(self):

        mag_V = 16.0
        passband = 'V'
        exp_time = 300
        spectrograph = 'F65-FLOYDS'
        params = { 'moon_phase' : 'G' }

        expected_mag = mag_V - 0.39
        expected_passband = 'ip'
        expected_snr = 34.2006627195866

        mag, new_passband, snr = calc_asteroid_snr(mag_V, passband, exp_time, instrument=spectrograph, params=params)

        self.assertEqual(expected_mag, mag)
        self.assertEqual(expected_passband, new_passband)
        self.assertAlmostEqual(expected_snr, snr, self.precision)
