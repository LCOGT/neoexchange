"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2026-2026 LCO

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
import shutil
import tempfile
from datetime import datetime
from io import StringIO

from astropy.io import fits
from django.core.management import call_command
from django.test import TestCase

from core.models import Block, Body, Frame, Proposal, SuperBlock
from core.views import determine_zp_aperture_radius, sync_e93_calibration
from photometrics.catalog_subs import fits_ldac_to_header, open_fits_catalog
from photometrics.external_codes import updateFITScalib


def set_ldac_header_keyword(ldac_file, keyword, value):
    """Sets <keyword> in the LDAC_IMHEAD of <ldac_file>, rebuilding the header table the way updateFITScalib does"""
    with fits.open(ldac_file) as hdulist:
        header = fits_ldac_to_header(hdulist[1].data[0][0])
        header[keyword] = value
        header_string = header.tostring(endcard=False)
        column = fits.Column(name='Field Header Card', format=f'{len(header_string)}A', array=[header_string])
        header_hdu = fits.BinTableHDU.from_columns(fits.ColDefs([column]))
        header_hdu.header['EXTNAME'] = 'LDAC_IMHEAD'
        header_hdu.header['TDIM1'] = f'(80, {len(header_string) // 80})'
        hdulist[1] = header_hdu
        hdulist.writeto(ldac_file, overwrite=True, checksum=True)


class SyncE93CalibrationTestCase(TestCase):
    """Fixtures: a Block with an e92 Frame calibrated by NEOx and an e93 Frame still carrying
    BANZAI's zeropoint, with matching files in a temporary data directory: the e92 (banzai_test_frame),
    its single-aperture LDAC (ldac_test_catalog, SEXAPED1 = 5.0 px) and the e93 + .rms.fits
    (hotpants_test_frame). None of the files has L1ZPAPER."""

    test_root = 'cpt1m013-kb76-20160606-0001'

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')
        fixtures = os.path.join('photometrics', 'tests')

        self.e92_file = os.path.join(self.test_dir, f'{self.test_root}-e92.fits')
        shutil.copy(os.path.join(fixtures, 'banzai_test_frame.fits'), self.e92_file)
        self.ldac_file = os.path.join(self.test_dir, f'{self.test_root}-e92_ldac.fits')
        shutil.copy(os.path.join(fixtures, 'ldac_test_catalog.fits'), self.ldac_file)
        # the 2016 fixture predates RLEVEL, which the BANZAI_LDAC mapping requires
        set_ldac_header_keyword(self.ldac_file, 'RLEVEL', 92)
        self.e93_file = os.path.join(self.test_dir, f'{self.test_root}-e93.fits')
        shutil.copy(os.path.join(fixtures, 'hotpants_test_frame.fits'), self.e93_file)
        self.e93_rms_file = os.path.join(self.test_dir, f'{self.test_root}-e93.rms.fits')
        shutil.copy(os.path.join(fixtures, 'hotpants_test_frame.rms.fits'), self.e93_rms_file)

        self.e92_calibration = {'zeropoint': 28.012, 'zeropoint_err': 0.0123, 'zeropoint_src': 'py_zp_cvc-V0.2.1',
                                'color_used': 'N/A', 'color': 0.0, 'color_err': 0.0, 'photometric_catalog': 'GAIA-DR3'}
        self.banzai_calibration = {'zeropoint': 27.5, 'zeropoint_err': 0.05, 'zeropoint_src': 'BANZAI'}
        updateFITScalib(self.e92_calibration, self.e92_file, 'BANZAI')
        updateFITScalib(self.e92_calibration, self.ldac_file, 'BANZAI_LDAC')
        updateFITScalib(self.banzai_calibration, self.e93_file, 'BANZAI')
        updateFITScalib(self.banzai_calibration, self.e93_rms_file, 'BANZAI')

        body_params = {'provisional_name': 'XL8B85F', 'origin': 'M', 'source_type': 'U', 'active': True,
                       'elements_type': 'MPC Minor Planet', 'epochofel': '2016-07-11 00:00:00', 'orbinc': 6.35992,
                       'longascnode': 108.82267, 'argofperih': 202.15361, 'eccentricity': 0.384586,
                       'meandist': 2.3057577, 'meananom': 352.55523, 'abs_mag': 21.3, 'slope': 0.15}
        self.body = Body.objects.create(**body_params)
        self.proposal = Proposal.objects.create(code='LCOTest', title='test', pi='bart.simpson@lcogt.net', tag='LCOGT', active=True)
        self.sblock = SuperBlock.objects.create(body=self.body, proposal=self.proposal, groupid='XL8B85F_CPT-20160606',
                                                block_start='2016-06-06 20:00:00', block_end='2016-06-07 03:00:00',
                                                tracking_number='00042', active=True)
        self.block = Block.objects.create(telclass='1m0', site='CPT', body=self.body, superblock=self.sblock,
                                          block_start='2016-06-06 20:00:00', block_end='2016-06-07 03:00:00',
                                          request_number='10042', num_exposures=5, exp_length=42.0, active=True)
        frame_params = {'sitecode': 'K92', 'instrument': 'kb76', 'filter': 'w', 'exptime': 225.0,
                        'midpoint': datetime(2016, 6, 6, 22, 48, 14), 'block': self.block}
        self.e92_frame = Frame.objects.create(filename=os.path.basename(self.e92_file), frametype=Frame.NEOX_RED_FRAMETYPE,
                                              **frame_params, **self.e92_calibration)
        self.e93_frame = Frame.objects.create(filename=os.path.basename(self.e93_file), frametype=Frame.NEOX_SUB_FRAMETYPE,
                                              **frame_params, **self.banzai_calibration)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def image_header(self, filepath):
        return fits.getheader(filepath)

    def ldac_header(self, filepath):
        header, _, _ = open_fits_catalog(filepath, header_only=True)
        return header

    def assert_e93_unchanged(self):
        self.e93_frame.refresh_from_db()
        self.assertEqual(27.5, self.e93_frame.zeropoint)
        self.assertEqual('BANZAI', self.e93_frame.zeropoint_src)
        for filepath in (self.e93_file, self.e93_rms_file):
            header = self.image_header(filepath)
            self.assertEqual(27.5, header['L1ZP'])
            self.assertEqual('BANZAI', header['L1ZPSRC'])
            self.assertNotIn('L1ZPAPER', header)
        self.assertNotIn('L1ZPAPER', self.image_header(self.e92_file))
        self.assertNotIn('L1ZPAPER', self.ldac_header(self.ldac_file))


class TestSyncE93Calibration(SyncE93CalibrationTestCase):

    def test_copies_e92_calibration_into_e93_frame_and_files(self):
        results = sync_e93_calibration(self.block, self.test_dir)

        self.assertEqual(1, len(results))
        result = results[0]
        self.assertEqual('ok', result['status'])
        self.assertEqual(self.e92_frame.filename, result['e92'])
        self.assertEqual(27.5, result['old_zeropoint'])
        self.assertEqual(28.012, result['new_zeropoint'])
        self.assertEqual(2.5, result['zp_aperture_pix'])
        self.assertEqual([os.path.basename(f) for f in (self.e93_file, self.e93_rms_file, self.e92_file, self.ldac_file)], result['files_updated'])
        self.assertEqual(["L1ZPAPER derived from the LDAC's SEXAPED1"], result['messages'])

        self.e93_frame.refresh_from_db()
        for field, value in self.e92_calibration.items():
            self.assertEqual(value, getattr(self.e93_frame, field), field)

        for filepath in (self.e93_file, self.e93_rms_file):
            header = self.image_header(filepath)
            self.assertEqual(28.012, header['L1ZP'], filepath)
            self.assertEqual(0.0123, header['L1ZPERR'])
            self.assertEqual('py_zp_cvc-V0.2.1', header['L1ZPSRC'])
            self.assertEqual(2.5, header['L1ZPAPER'])
            self.assertEqual('N/A', header['L1COLORU'])
            self.assertEqual(0.0, header['L1COLOR'])
            self.assertEqual(0.0, header['L1COLERR'])
            self.assertEqual('GAIA-DR3', header['L1PHTCAT'])
        self.assertEqual(2.5, self.image_header(self.e92_file)['L1ZPAPER'])
        self.assertEqual(28.012, self.image_header(self.e92_file)['L1ZP'])
        self.assertEqual(2.5, self.ldac_header(self.ldac_file)['L1ZPAPER'])
        self.assertEqual(28.012, self.ldac_header(self.ldac_file)['L1ZP'])

    def test_dry_run_changes_nothing(self):
        results = sync_e93_calibration(self.block, self.test_dir, dry_run=True)

        self.assertEqual('ok', results[0]['status'])
        self.assertEqual(28.012, results[0]['new_zeropoint'])
        self.assertEqual(2.5, results[0]['zp_aperture_pix'])
        self.assertEqual(4, len(results[0]['files_updated']))
        self.assert_e93_unchanged()

    def test_rerun_is_idempotent(self):
        sync_e93_calibration(self.block, self.test_dir)
        results = sync_e93_calibration(self.block, self.test_dir)

        self.assertEqual('ok', results[0]['status'])
        self.assertEqual(28.012, results[0]['old_zeropoint'])
        self.assertEqual(2.5, results[0]['zp_aperture_pix'])
        # L1ZPAPER now comes from the e92 header, nothing derived
        self.assertEqual([], results[0]['messages'])
        self.assertEqual(28.012, self.image_header(self.e93_file)['L1ZP'])

    def test_e92_with_banzai_zeropoint_is_reported_not_copied(self):
        self.e92_frame.zeropoint_src = 'BANZAI'
        self.e92_frame.save()

        results = sync_e93_calibration(self.block, self.test_dir)

        self.assertEqual('e92 has no NEOx zeropoint', results[0]['status'])
        self.assertEqual(self.e92_frame.filename, results[0]['e92'])
        self.assertIn("zeropoint_src='BANZAI'", results[0]['messages'][0])
        self.assert_e93_unchanged()

    def test_e92_with_failed_zeropoint_is_reported_not_copied(self):
        self.e92_frame.zeropoint = -99.0
        self.e92_frame.save()

        results = sync_e93_calibration(self.block, self.test_dir)

        self.assertEqual('e92 has no NEOx zeropoint', results[0]['status'])
        self.assert_e93_unchanged()

    def test_missing_e92_frame_is_reported(self):
        self.e92_frame.delete()

        results = sync_e93_calibration(self.block, self.test_dir)

        self.assertEqual('no e92 Frame', results[0]['status'])
        self.assertIsNone(results[0]['e92'])
        self.assert_e93_unchanged()

    def test_missing_files_are_reported_but_frame_is_updated(self):
        os.remove(self.e93_rms_file)
        os.remove(self.ldac_file)

        results = sync_e93_calibration(self.block, self.test_dir)

        result = results[0]
        self.assertEqual('ok', result['status'])
        self.assertIsNone(result['zp_aperture_pix'])
        self.assertEqual([os.path.basename(self.e93_file), os.path.basename(self.e92_file)], result['files_updated'])
        self.assertTrue(any('no LDAC' in m for m in result['messages']), result['messages'])
        self.assertTrue(any('without L1ZPAPER' in m for m in result['messages']), result['messages'])
        self.assertTrue(any(f'{self.test_root}-e93.rms.fits not found' in m for m in result['messages']), result['messages'])
        self.e93_frame.refresh_from_db()
        self.assertEqual(28.012, self.e93_frame.zeropoint)
        header = self.image_header(self.e93_file)
        self.assertEqual(28.012, header['L1ZP'])
        self.assertNotIn('L1ZPAPER', header)

    def test_existing_e92_l1zpaper_takes_precedence_over_ldac(self):
        updateFITScalib({'zeropoint_aperture_pixels': 6.0}, self.e92_file, 'BANZAI')

        results = sync_e93_calibration(self.block, self.test_dir)

        self.assertEqual(6.0, results[0]['zp_aperture_pix'])
        self.assertEqual([], results[0]['messages'])
        self.assertEqual(6.0, self.image_header(self.e93_file)['L1ZPAPER'])
        self.assertEqual(6.0, self.ldac_header(self.ldac_file)['L1ZPAPER'])

    def test_no_e93_frames(self):
        self.e93_frame.delete()

        self.assertEqual([], sync_e93_calibration(self.block, self.test_dir))


class TestDetermineZpApertureRadius(SyncE93CalibrationTestCase):

    def test_single_aperture_ldac(self):
        radius, message = determine_zp_aperture_radius(self.e92_file, self.ldac_file)

        self.assertEqual(2.5, radius)
        self.assertEqual("L1ZPAPER derived from the LDAC's SEXAPED1", message)

    def test_multi_aperture_ldac_uses_marked_config_aperture(self):
        shutil.copy(os.path.join('photometrics', 'tests', 'banzai_test_multiaper_ldac.fits'), self.ldac_file)
        shutil.copy(os.path.join('photometrics', 'configs', 'sextractor_neox_ldac_multiaper.conf'), self.test_dir)

        radius, message = determine_zp_aperture_radius(self.e92_file, self.ldac_file)

        self.assertEqual(11.0, radius)
        self.assertEqual("L1ZPAPER derived from the multi-aperture LDAC (aperture 5 of 11)", message)

    def test_multi_aperture_ldac_without_config(self):
        shutil.copy(os.path.join('photometrics', 'tests', 'banzai_test_multiaper_ldac.fits'), self.ldac_file)

        radius, message = determine_zp_aperture_radius(self.e92_file, self.ldac_file)

        self.assertIsNone(radius)
        self.assertIn('no sextractor_neox_ldac_multiaper.conf beside it', message)

    def test_ldac_l1zpaper_used_when_e92_lacks_it(self):
        updateFITScalib({'zeropoint_aperture_pixels': 7.5}, self.ldac_file, 'BANZAI_LDAC')

        radius, message = determine_zp_aperture_radius(self.e92_file, self.ldac_file)

        self.assertEqual(7.5, radius)
        self.assertIsNone(message)

    def test_no_files(self):
        radius, message = determine_zp_aperture_radius(os.path.join(self.test_dir, 'nope-e92.fits'), os.path.join(self.test_dir, 'nope-e92_ldac.fits'))

        self.assertIsNone(radius)
        self.assertIn('no LDAC nope-e92_ldac.fits', message)


class TestFixE93ZeropointsCommand(SyncE93CalibrationTestCase):

    def test_command_repairs_block(self):
        out = StringIO()
        call_command('fix_e93_zeropoints', self.test_dir, block=self.block.id, stdout=out)

        output = out.getvalue()
        self.assertIn(f"{self.test_root}-e93.fits: L1ZP 27.5 -> 28.012 (py_zp_cvc-V0.2.1), L1ZPAPER 2.5 px", output)
        self.assertIn("1 of 1 e93 Frames repaired", output)
        self.e93_frame.refresh_from_db()
        self.assertEqual(28.012, self.e93_frame.zeropoint)

    def test_command_dry_run(self):
        out = StringIO()
        call_command('fix_e93_zeropoints', self.test_dir, block=self.block.id, dry_run=True, stdout=out)

        self.assertIn("(dry-run) 1 of 1 e93 Frames repaired", out.getvalue())
        self.assert_e93_unchanged()

    def test_command_reports_uncalibrated_e92(self):
        self.e92_frame.zeropoint_src = 'BANZAI'
        self.e92_frame.save()
        out = StringIO()
        call_command('fix_e93_zeropoints', self.test_dir, block=self.block.id, stdout=out)

        output = out.getvalue()
        self.assertIn("NOT REPAIRED (e92 has no NEOx zeropoint)", output)
        self.assertIn("0 of 1 e93 Frames repaired; problems: e92 has no NEOx zeropoint", output)

    def test_command_bad_block(self):
        with self.assertRaisesMessage(Exception, "Block ID 999999 does not exist."):
            call_command('fix_e93_zeropoints', self.test_dir, block=999999, stdout=StringIO())
