"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2022-2022 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

import os
from glob import glob
from datetime import datetime, date, timedelta
import tempfile
from unittest import skipIf
import warnings
import shutil
from pathlib import Path

from astropy.io import fits
from astropy.wcs import WCS
from numpy import array, arange
from numpy.testing import assert_allclose

from django.test import TestCase
from django.forms.models import model_to_dict

from core.models import Body, StaticSource, Block, Frame
from photometrics.tests.test_external_codes import ExternalCodeUnitTest
# Import module to test
from photometrics.image_subs import *

# Disable logging during testing
import logging
logger = logging.getLogger(__name__)
# Disable anything below CRITICAL level
logging.disable(logging.CRITICAL)

class TestCreateWeightImage(ExternalCodeUnitTest):
    def setUp(self):
        super(TestCreateWeightImage, self).setUp()
        self.test_banzai_file = os.path.join(self.testfits_dir, 'banzai_test_frame.fits')
        self.test_banzai_comp_file = os.path.join(self.testfits_dir, 'banzai_test_frame.fits.fz')
        self.test_banzai_rms_file = os.path.join(self.testfits_dir, 'banzai_test_frame.rms.fits')

        """example-sbig-e10.fits"""
        # This image only has a 'PRIMARY' HDU
        shutil.copy(os.path.abspath(self.test_fits_file), self.test_dir)
        self.test_fits_file = os.path.join(self.test_dir, os.path.basename(self.test_fits_file))

        """banzai_test_frame.fits"""
        shutil.copy(os.path.abspath(self.test_banzai_file), self.test_dir)
        self.test_banzai_file = os.path.join(self.test_dir, os.path.basename(self.test_banzai_file))

        """banzai_test_frame.fits.fz"""
        shutil.copy(os.path.abspath(self.test_banzai_comp_file), self.test_dir)
        self.test_banzai_comp_file = os.path.join(self.test_dir, os.path.basename(self.test_banzai_comp_file))

        """banzai_test_frame.rms.fits"""
        shutil.copy(os.path.abspath(self.test_banzai_rms_file), self.test_dir)
        self.test_banzai_rms_file = os.path.join(self.test_dir, os.path.basename(self.test_banzai_rms_file))

        """swarp_neox.conf"""
        shutil.copy(os.path.abspath(os.path.join(self.source_dir, 'swarp_neox.conf')), self.test_dir)
        self.test_conf_file = os.path.join(self.test_dir, 'swarp_neox.conf')

        self.remove = True

    def test_doesnotexist(self):
        expected_status = -11

        status = create_weight_image('banana.fits')

        self.assertEqual(expected_status, status)

    def test_badfitsfile(self):
        expected_status = -12

        bad_file = os.path.join(self.source_dir, 'swarp_neox.conf')
        status = create_weight_image(bad_file)

        self.assertEqual(expected_status, status)

    def test_noscihdu(self):
        expected_status = -13

        status = create_weight_image(self.test_fits_file)

        self.assertEqual(expected_status, status)

    def test_nobpmhdu(self):
        expected_status = -14

        with fits.open(self.test_fits_file) as hdulist:
            # Rename the 'PRIMARY' HDU to 'SCI'
            header = hdulist[0].header
            header['EXTNAME'] = 'SCI'
            hdulist.writeto(self.test_fits_file, overwrite=True, checksum=True)

        status = create_weight_image(self.test_fits_file)

        self.assertEqual(expected_status, status)

    def test_does_not_contain_fits(self):
        # A fits file that has all the correct HDUs and an rms file, but somehow does not contain ".fits"
        expected_status = -15

        bad_file = self.test_banzai_comp_file.replace(".fits.fz", ".pear")
        os.rename(self.test_banzai_comp_file, bad_file)

        status = create_weight_image(bad_file)

        self.assertEqual(expected_status, status)

    def test_rms_doesnotexist(self):
        expected_status = -16

        os.remove(self.test_banzai_rms_file)
        status = create_weight_image(self.test_banzai_file)

        self.assertEqual(expected_status, status)

    def test_rms_badfitsfile(self):
        # Rename a non-fits file to be the rms file
        expected_status = -17

        good_file = self.test_banzai_file
        bad_rms = self.test_conf_file
        os.replace(bad_rms, self.test_banzai_rms_file)

        status = create_weight_image(good_file)

        self.assertEqual(expected_status, status)

    def test_rms_badhdus(self):
        #Wrong number of HDUs in the rms file
        expected_status = -18

        good_file = self.test_banzai_file
        bad_rms = self.test_banzai_comp_file
        os.replace(bad_rms, self.test_banzai_rms_file)

        status = create_weight_image(good_file)

        self.assertEqual(expected_status, status)


    def test_does_not_modify_input(self):
        expected_filename = self.test_banzai_file.replace(".fits", ".weights.fits")

        weight_filename = create_weight_image(self.test_banzai_file)

        self.assertEqual(expected_filename, weight_filename)

        # Ensuring that the input file has NOT been overwritten with the weight data
        header = fits.getheader(self.test_banzai_file, 0)
        self.assertEqual('SCI', header.get('EXTNAME', ''))
        self.assertTrue('L1FRMTYP' not in header)
        self.assertNotEqual('WEIGHT', header.get('L1FRMTYP', ''))

        header = fits.getheader(weight_filename, 0)
        self.assertEqual('', header.get('EXTNAME', ''))
        self.assertEqual('WEIGHT', header.get('L1FRMTYP', ''))

    def test_success(self):
        expected_filename = self.test_banzai_file.replace(".fits", ".weights.fits")

        weight_filename = create_weight_image(self.test_banzai_file)

        self.assertEqual(expected_filename, weight_filename)


        with fits.open(weight_filename) as hdul:
            header = hdul[0].header
            data = hdul[0].data

        self.assertEqual('', header.get('EXTNAME', ''))
        self.assertEqual('WEIGHT', header.get('L1FRMTYP', ''))
        # Test whether saturated pixels are 0.0
        assert_allclose(0.0, data[444, 394])
        # Test whether bad pixels are 0.0
        assert_allclose(0.0, data[1653:1663, 458])
        # Test whether central pixel is nonzero
        assert_allclose(0.0009511118, data[int(header['NAXIS1']/2), int(header['NAXIS2']/2)])


class TestCreateRMSImage(ExternalCodeUnitTest):
    def setUp(self):
        super(TestCreateRMSImage, self).setUp()
        self.test_fits_weight_file = os.path.join(self.testfits_dir, 'example-sbig-e10.weight.fits')

        """example-sbig-e10.fits"""
        # This image only has a 'PRIMARY' HDU
        shutil.copy(os.path.abspath(self.test_fits_file), self.test_dir)
        self.test_fits_file = os.path.join(self.test_dir, os.path.basename(self.test_fits_file))

        """example-sbig-e10.weight.fits"""
        shutil.copy(os.path.abspath(self.test_fits_weight_file), self.test_dir)
        self.test_fits_weight_file = os.path.join(self.test_dir, os.path.basename(self.test_fits_weight_file))

        """swarp_neox.conf"""
        shutil.copy(os.path.abspath(os.path.join(self.source_dir, 'swarp_neox.conf')), self.test_dir)
        self.test_conf_file = os.path.join(self.test_dir, 'swarp_neox.conf')

        self.remove = True

    def test_doesnotexist(self):
        expected_status = -11

        status = create_rms_image('banana.fits')

        self.assertEqual(expected_status, status)

    def test_badfitsfile(self):
        expected_status = -12

        bad_file = os.path.join(self.source_dir, 'swarp_neox.conf')
        status = create_rms_image(bad_file)

        self.assertEqual(expected_status, status)

    def test_does_not_contain_fits(self):
        # A fits file that somehow does not contain ".fits"
        expected_status = -15

        bad_file = self.test_fits_file.replace(".fits", ".pear")
        os.rename(self.test_fits_file, bad_file)

        status = create_rms_image(bad_file)

        self.assertEqual(expected_status, status)

    def test_weight_doesnotexist(self):
        expected_status = -16

        os.remove(self.test_fits_weight_file)
        status = create_rms_image(self.test_fits_file)

        self.assertEqual(expected_status, status)

    def test_weight_badfitsfile(self):
        # Rename a non-fits file to be the weight file
        expected_status = -17

        good_file = self.test_fits_file
        bad_weight = self.test_conf_file
        os.replace(bad_weight, self.test_fits_weight_file)

        status = create_rms_image(good_file)

        self.assertEqual(expected_status, status)

    def test_weight_badhdus(self):
        #Wrong number of HDUs in the weight file
        expected_status = -18

        fits.append(self.test_fits_weight_file, np.empty(0))

        status = create_rms_image(self.test_fits_file)

        self.assertEqual(expected_status, status)

    def test_does_not_modify_input(self):
        expected_filename = self.test_fits_weight_file.replace(".weight.fits", ".rms.fits")

        rms_filename = create_rms_image(self.test_fits_file)

        self.assertEqual(expected_filename, rms_filename)

        # Ensuring that the input file has NOT been overwritten with the weight data
        header = fits.getheader(self.test_fits_file, 0)
        self.assertTrue('L1FRMTYP' not in header)

        header = fits.getheader(rms_filename, 0)
        self.assertTrue('L1FRMTYP' in header)

    def test_success(self):
        expected_filename = self.test_fits_weight_file.replace(".weight.fits", ".rms.fits")

        rms_filename = create_rms_image(self.test_fits_file)

        self.assertEqual(expected_filename, rms_filename)

        with fits.open(rms_filename) as hdul:
            header = hdul[0].header
            data = hdul[0].data

        self.assertEqual('RMS', header.get('L1FRMTYP', ''))
        # Test whether saturated pixels have appropriate RMS value
        assert_allclose(223.6068, data[1000, 458])
        # Test whether central pixel is not saturated
        assert_allclose(25.846653, data[int(header['NAXIS1']/2), int(header['NAXIS2']/2)])

    def test_modified_MAXLIN(self):
        #manually override the MAXLIN value in the test image to make sure it's working right
        expected_filename = self.test_fits_weight_file.replace(".weight.fits", ".rms.fits")

        #sci_header = fits.getheader(self.test_fits_file)
        #sci_header['MAXLIN'] = 40000

        fits.setval(self.test_fits_file, 'MAXLIN', value=10000)

        rms_filename = create_rms_image(self.test_fits_file)

        self.assertEqual(expected_filename, rms_filename)

        with fits.open(rms_filename) as hdul:
            header = hdul[0].header
            data = hdul[0].data

        self.assertEqual('RMS', header.get('L1FRMTYP', ''))
        # Test whether saturated pixels have appropriate RMS value
        assert_allclose(223.6068, data[1007, 367])
        # Test whether central pixel is not saturated
        assert_allclose(25.846653, data[int(header['NAXIS1']/2), int(header['NAXIS2']/2)])

class TestGetReferenceName(ExternalCodeUnitTest):

    def test_ra_1dig_dec_p1dig(self):
        expected_status = "reference_lsc_fa15_w_001.11_+04.44.fits"

        status = get_reference_name(1.111, 4.444,  "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_ra_1dig_dec_p2dig(self):
        expected_status = "reference_lsc_fa15_w_001.11_+84.44.fits"

        status = get_reference_name(1.111, 84.444,  "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_ra_1dig_dec_m1dig(self):
        expected_status = "reference_lsc_fa15_w_001.11_-04.44.fits"

        status = get_reference_name(1.111, -4.444,  "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_ra_1dig_dec_m2dig(self):
        expected_status = "reference_lsc_fa15_w_001.11_-84.44.fits"

        status = get_reference_name(1.111, -84.444,  "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_ra_2dig_dec_p1dig(self):
        expected_status = "reference_lsc_fa15_w_011.11_+04.44.fits"

        status = get_reference_name(11.111, 4.444,  "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_ra_2dig_dec_p2dig(self):
        expected_status = "reference_lsc_fa15_w_011.11_+84.44.fits"

        status = get_reference_name(11.111, 84.444,  "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_ra_2dig_dec_m1dig(self):
        expected_status = "reference_lsc_fa15_w_011.11_-04.44.fits"

        status = get_reference_name(11.111, -4.444,  "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_ra_2dig_dec_m2dig(self):
        expected_status = "reference_lsc_fa15_w_011.11_-84.44.fits"

        status = get_reference_name(11.111, -84.444,  "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_ra_3dig_dec_p1dig(self):
        expected_status = "reference_lsc_fa15_w_111.11_+04.44.fits"

        status = get_reference_name(111.111, 4.444,  "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_ra_3dig_dec_p2dig(self):
        expected_status = "reference_lsc_fa15_w_111.11_+84.44.fits"

        status = get_reference_name(111.111, 84.444,  "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_ra_3dig_dec_m1dig(self):
        expected_status = "reference_lsc_fa15_w_111.11_-04.44.fits"

        status = get_reference_name(111.111, -4.444,  "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_ra_3dig_dec_m2dig(self):
        expected_status = "reference_lsc_fa15_w_111.11_-84.44.fits"

        status = get_reference_name(111.111, -84.444,  "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_obs_date_datetime(self):
        expected_status = "reference_coj_ep06_gp_111.11_-84.44_20240511.fits"

        status = get_reference_name(111.111, -84.444,  "coj", "ep06", "gp", datetime(2024,5,11))

        self.assertEqual(expected_status, status)

    def test_obs_date_full_datetime(self):
        expected_status = "reference_coj_ep06_gp_111.11_-84.44_20240511.fits"

        status = get_reference_name(111.111, -84.444,  "coj", "ep06", "gp", datetime(2024,5,11,23,59,59))

        self.assertEqual(expected_status, status)

    def test_bad_obs_date(self):
        expected_status = -98

        status = get_reference_name(111.111, -84.444,  "coj", "ep06", "gp", 2024511)

        self.assertEqual(expected_status, status)

    def test_bad_coords_type_string(self):
        expected_status = -1

        status = get_reference_name("string", "string", "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_bad_coords_type_int(self):
        expected_status = -1

        status = get_reference_name(1, 1, "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_bad_site_type(self):
        expected_status = -99

        status = get_reference_name(111.111, 4.444, 1, "fa15", "w")

        self.assertEqual(expected_status, status)


class TestFindReferenceImage(ExternalCodeUnitTest):
    def test1(self):
        newfile1 = os.path.join(self.test_dir, "reference_222.22_-33.33_cpt_w.fits")
        newfile2 = os.path.join(self.test_dir, "reference_444.44_-55.55_lsc_rp.fits")
        newfile3 = os.path.join(self.test_dir, "cpt1m0.fits")
        Path(newfile1).touch()
        Path(newfile2).touch()
        Path(newfile3).touch()

        expected_output = [newfile1, newfile2]

        output = find_reference_images(self.test_dir, "reference*.fits")

        self.assertEqual(expected_output, output)

    def test2(self):
        newfile1 = os.path.join(self.test_dir, "reference_222.22_-33.33_cpt_w.fits")
        newfile2 = os.path.join(self.test_dir, "reference_444.44_-55.55_lsc_rp.fits")
        newfile3 = os.path.join(self.test_dir, "cpt1m0.fits")
        Path(newfile1).touch()
        Path(newfile2).touch()
        Path(newfile3).touch()

        expected_output = [newfile1]

        output = find_reference_images(self.test_dir, "reference*cpt*.fits")

        self.assertEqual(expected_output, output)

class TestDetermineReferenceFieldForBlock(TestCase):
    def setUp(self):
        body_params = {
                         'provisional_name': None,
                         'provisional_packed': None,
                         'name': '65803',
                         'origin': 'N',
                         'source_type': 'N',
                         'source_subtype_1': 'N3',
                         'source_subtype_2': 'PH',
                         'elements_type': 'MPC_MINOR_PLANET',
                         'active': True,
                         'fast_moving': False,
                         'urgency': None,
                         'epochofel': datetime(2024, 3, 31, 0, 0),
                         'orbit_rms': 0.71,
                         'orbinc': 3.41422,
                         'longascnode': 72.98677,
                         'argofperih': 319.59164,
                         'eccentricity': 0.3832302,
                         'meandist': 1.6426815,
                         'meananom': 246.30743,
                         'perihdist': None,
                         'epochofperih': None,
                         'abs_mag': 18.11,
                         'slope': 0.15,
                         'score': None,
                         'discovery_date': datetime(1996, 4, 11, 0, 0),
                         'num_obs': 5304,
                         'arc_length': 9923.0,
                         'not_seen': 359.8285771261227,
                         'updated': True,
                         'ingest': datetime(2018, 8, 14, 17, 45, 42),
                         'update_time': datetime(2024, 7, 29, 19, 54, 13, 688594),
                         'analysis_status': 0,
                         'as_updated': None}
        self.test_body, created = Body.objects.get_or_create(**body_params)
        statsrc_params = {
                            'name' : '',
                            'ra' : None,
                            'dec' : None,
                            'vmag': 9.0,
                            'spectral_type': '',
                            'source_type': StaticSource.REFERENCE_FIELD,
                            'notes': '',
                            'quality': 0,
                            'reference': ''}
        field_names = ['Didymos COJ 2024 Field v2 #20', 'Didymos COJ 2024 Field v2 #26']
        field_coords = [(264.624525, -28.36852), (262.5789150, -28.514)]
        self.test_ref_fields = []
        for name, coords in zip(field_names, field_coords):
            statsrc_params['name'] = name
            statsrc_params['ra'] = coords[0]
            statsrc_params['dec'] = coords[1]
            ref_field, created = StaticSource.objects.get_or_create(**statsrc_params)
            self.test_ref_fields.append(ref_field)

        block_params = {
                         'telclass': '2m0',
                         'site': 'coj',
                         'body': self.test_body,
                         'calibsource': self.test_ref_fields[0],
                         'obstype': Block.OPT_IMAGING,
                         'block_start': datetime(2024, 7, 30, 0, 0),
                         'block_end': datetime(2024, 7, 30, 23, 59, 59),
                         'request_number': '3602880',
                         'num_exposures': 125,
                         'exp_length': 170.0,
                         'num_observed': 1,
                         'when_observed': datetime(2024, 7, 30, 15, 32, 9),
                         'active': False,
                         'reported': False,
                         'when_reported': None,
                         'tracking_rate': 0}
        self.test_block_both, created = Block.objects.get_or_create(**block_params)
        block_params['body'] = None
        self.test_block_calibsrc_only, created = Block.objects.get_or_create(**block_params)
        block_params['body'] = self.test_body
        block_params['calibsource'] = None
        self.test_block_body_only, created = Block.objects.get_or_create(**block_params)

        # Hand-rolled WCS for testing
        naxis_header = {'NAXIS1' : 2048, 'NAXIS2' : 2048, 'NAXIS' : 2,
                        'CTYPE1' : 'RA---TAN', 'CTYPE2' : 'DEC--TAN',
                        'CRPIX1' : 1024.0, 'CRPIX2' : 1024.0,
                        'CRVAL1' : 264.626, 'CRVAL2' : -28.36854
                        }
        self.test_wcs = WCS(naxis_header)
        pixscale = 0.2666/3600.0
        self.test_wcs.wcs.cd = np.array([[-pixscale, 0],[0, pixscale]])
        orig_params = { 
                         'sitecode': 'E10',
                         'instrument': 'ep07',
                         'filter': 'rp',
                         'filename': 'coj2m002-ep07-20240729-0100-e92.fits',
                         'exptime': 170.0,
                         'midpoint': datetime(2024, 7, 29, 11, 25, 52),
                         'block': self.test_block_both,
                         'quality': ' ',
                         'zeropoint': 23.5,
                         'zeropoint_err': 0.04,
                         'zeropoint_src': 'py_zp_cvc-V0.2.1',
                         'fwhm': 2.14,
                         'frametype': 92,
                         'rms_of_fit': 0.167375,
                         'nstars_in_fit': 1627.0,
                         'astrometric_catalog': 'GAIA-DR2',
                         'photometric_catalog': 'PS1',
                         'wcs' : self.test_wcs
                       }
        for frame_num in range(100, 103):
            frame_params = orig_params.copy()
            frame_params['filename'] = f'coj2m002-ep07-20240729-{frame_num:04d}-e92.fits'
            inc_frames = frame_num-100
            frame_params['midpoint'] = frame_params['midpoint'] + timedelta(seconds=inc_frames*(frame_params['exptime'] + 10))
            for block in [self.test_block_both,  self.test_block_calibsrc_only, self.test_block_body_only]:
                frame_params['block'] = block
                frame, created = Frame.objects.get_or_create(**frame_params)

    def test_basics(self):
        expected_num_body = 1
        expected_num_statsrc = 2
        expected_num_blocks = 3
        expected_num_frames = 3 * 3

        self.assertEqual(expected_num_body, Body.objects.all().count())
        self.assertEqual(expected_num_statsrc, StaticSource.objects.all().count())
        self.assertEqual(expected_num_statsrc, StaticSource.objects.filter(source_type=StaticSource.REFERENCE_FIELD).count())
        self.assertEqual(expected_num_blocks, Block.objects.all().count())
        self.assertEqual(expected_num_frames, Frame.objects.all().count())

    def test_calibsrc_only(self):
        expected_field = self.test_ref_fields[0]

        field = determine_reffield_for_block(self.test_block_calibsrc_only)

        self.assertEqual(expected_field, field)

    def test_bad_calibsrc(self):
        # Invalidate StaticSource type
        self.test_block_calibsrc_only.calibsource.source_type = StaticSource.FLUX_STANDARD
        self.test_block_calibsrc_only.calibsource.name = 'HZ 44'
        self.test_block_calibsrc_only.save()
        
        expected_field = self.test_ref_fields[0]

        field = determine_reffield_for_block(self.test_block_calibsrc_only)

        self.assertEqual(expected_field, field)

    def test_body_only(self):
        expected_field = self.test_ref_fields[0]

        field = determine_reffield_for_block(self.test_block_body_only)

        self.assertEqual(expected_field, field)

    def test_both(self):
        expected_field = self.test_ref_fields[0]

        field = determine_reffield_for_block(self.test_block_both)

        self.assertEqual(expected_field, field)


class TestDetermineReferenceFrameForBlock(ExternalCodeUnitTest):
    def setUp(self):
        super(TestDetermineReferenceFrameForBlock, self).setUp()
        self.test_refframes = {'field1' : { 'gp' : 'reference_coj_ep06_gp_264.62_-28.37_20240721.fits',
                                            'rp' : 'reference_coj_ep07_rp_264.62_-28.37_20240721.fits'
                                           },
                               'field2' : { 'gp' : 'reference_coj_ep06_gp_262.58_-28.51_20240722.fits',
                                            'rp' : 'reference_coj_ep07_rp_262.58_-28.51_20240722.fits'
                                           }
                              }
        for filename in list(self.all_vals(self.test_refframes)):
            newfile1 = os.path.join(self.test_dir, filename)
            Path(newfile1).touch()

        self.test_block = None

        self.debug_print = True
        self.remove = False

    def all_vals(self, obj):
        if isinstance(obj, dict):
            for v in obj.values():
                yield from self.all_vals(v)
        else:
            yield obj
        
    def test_field1_gp(self):
        expected_name = self.test_refframes['field1']['gp']

        ref_name = determine_reference_frame_for_block(self.test_block, 'gp', self.test_dir)

        self.assertEqual(expected_name, ref_name)

