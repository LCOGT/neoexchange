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

class SNRTestCase(TestCase):
    def __init__(self, *args, **kwargs):
        super(SNRTestCase, self).__init__(*args, **kwargs)

    def setUp(self):

        self.ftn_zp = 25.3
        self.fts_zp = 23.1

        self.precision = 4
        self.expected_units = u.Unit('ph/(s*cm**2*AA)')

        self.ftn_tic_params = { 'zp_i'      : self.ftn_zp,
                                'sky_mag_i' : 19.3,
                                'read_noise': 3.7,
                                'eff_area'  : 2.84*u.meter**2,
                                'flux_mag0' : 3631.0*u.Jy,
                                'wavelength': 752.0*u.nm,
                                'filter'    : 'ip',
                                'num_mirrors' : 3,  # Tertiary fold mirror
                                'instrument_eff' : 0.42,
                                'grating_eff' : 0.60,
                                'ccd_qe'    : 0.70
                              }
        self.wht_tic_params = { 'zp_i'      : 17.271,
                                'sky_mag_i' : 20.0,
                                'read_noise': 3.9,
                                'eff_area'  : 12.47*u.meter**2,
                                'flux_mag0' : 2550.0*u.Jy,
                                'wavelength': 820.0*u.nm,
                                'filter'    : 'I',
                                'instrument_eff' : 0.42,
                                'grating_eff' : 0.60,
                                'ccd_qe'    : 0.80,
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

       expected_snr = 5.42

       snr = compute_floyds_snr(mag_I, exp_time, self.wht_tic_params, emulate_signal=True)

       self.assertAlmostEqual(expected_snr, snr, self.precision)

    def test_faint_ftn1(self):

        mag_i = 18.0
        exp_time = 100.0

        expected_snr = 42.0

        snr =  compute_floyds_snr(mag_i, exp_time, self.ftn_tic_params)

        self.assertAlmostEqual(expected_snr, snr, self.precision)
