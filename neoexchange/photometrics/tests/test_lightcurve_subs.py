import os
import shutil
import tempfile
from glob import glob
from datetime import datetime, timedelta

import numpy as np
from astropy.table import Column, Table
from astropy.time import Time
from astropy.wcs import WCS

from core.models import Body, SuperBlock, Block, Frame, SourceMeasurement
from photometrics.lightcurve_subs import *

from django.test import SimpleTestCase, TestCase
from numpy.testing import assert_allclose, assert_array_equal

class TestReadPhotomPipe(SimpleTestCase):

    def setUp(self):
        self.test_lc_file = os.path.abspath(os.path.join('photometrics', 'tests', 'example_photompipe.dat'))

        self.debug_print = False
        self.maxDiff = None


    def test_read(self):
        expected_length = 62

        table = read_photompipe_file(self.test_lc_file)

        self.assertEqual(expected_length, len(table))

class TestWriteDartFormatFile(SimpleTestCase):

    def setUp(self):
        test_lc_file = os.path.abspath(os.path.join('photometrics', 'tests', 'example_photompipe.dat'))

        self.test_table = read_photompipe_file(test_lc_file)
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')

        self.remove = True
        self.debug_print = False
        self.maxDiff = None

    def tearDown(self):
        if self.remove:
            try:
                files_to_remove = glob(os.path.join(self.test_dir, '*'))
                for file_to_rm in files_to_remove:
                    os.remove(file_to_rm)
            except OSError:
                print("Error removing files in temporary test directory", self.test_dir)
            try:
                os.rmdir(self.test_dir)
                if self.debug_print:
                    print("Removed", self.test_dir)
            except OSError:
                print("Error removing temporary test directory", self.test_dir)
        else:
            if self.debug_print:
                print("Test directory", self.test_dir, "not removed")

    def test_write(self):
        expected_lines = [
        '                                 file      julian_date      mag     sig       ZP  ZP_sig  inst_mag  inst_sig  filter  SExtractor_flag  aprad',
        ' tfn1m001-fa11-20211012-0073-e92.fits  2459500.3339392  14.8400  0.0397  27.1845  0.0394  -12.3397    0.0052       r                0  10.00',
        ' tfn1m001-fa11-20211012-0074-e92.fits  2459500.3345790  14.8637  0.0293  27.1824  0.0300  -12.3187    0.0053       r                3  10.00'
        ]

        # Modify some values to test rounding
        self.test_table[0]['mag'] = 14.84
        self.test_table[1]['ZP_sig'] = 0.03
        output_file = os.path.join(self.test_dir, 'test.tab')
        write_dartformat_file(self.test_table[0:2], output_file, aprad=10)

        with open(output_file, 'r') as table_file:
            lines = table_file.readlines()

        self.assertEqual(3, len(lines))
        for i, expected_line in enumerate(expected_lines):
            self.assertEqual(expected_line, lines[i].rstrip())

    def test_write_swope(self):
        expected_lines = [
        '                                 file      julian_date      mag     sig       ZP  ZP_sig  inst_mag  inst_sig  filter  SExtractor_flag  aprad',
        '                        rccd0073.fits  2459500.3339392  14.8400  0.0397  27.1845  0.0394  -12.3397    0.0052       r                0  10.00',
        '                        rccd0074.fits  2459500.3345790  14.8637  0.0293  27.1824  0.0300  -12.3187    0.0053       r                3  10.00'
        ]

        # Modify some values to test rounding and different filenames
        new_names =  ["{:>36s}".format(x.replace('tfn1m001-fa11-20211012-', 'rccd').replace('-e91.lda', '.ldac')) for x in self.test_table['filename']]
        self.test_table.replace_column('filename', Column(new_names))
        self.test_table[0]['mag'] = 14.84
        self.test_table[1]['ZP_sig'] = 0.03
        output_file = os.path.join(self.test_dir, 'test.tab')
        write_dartformat_file(self.test_table[0:2], output_file, aprad=10)

        with open(output_file, 'r') as table_file:
            lines = table_file.readlines()

        self.assertEqual(3, len(lines))
        for i, expected_line in enumerate(expected_lines):
            self.assertEqual(expected_line, lines[i].rstrip())


class TestExtractApRadius(SimpleTestCase):

    def setUp(self):
        self.test_logfile = os.path.abspath(os.path.join('photometrics', 'tests', 'example_photompipe_log'))

    def test_nofile(self):

        aper_radius = extract_photompipe_aperradius('/foo/bar/log')

        self.assertEqual(None, aper_radius)

    def test_log(self):
        expected_radius = 10.0

        aper_radius = extract_photompipe_aperradius(self.test_logfile)

        self.assertEqual(expected_radius, aper_radius)

class TestCreateTableFromSrcMeasure(TestCase):

    def setUp(self):

        body_params = {
                         'id': 36254,
                         'provisional_name': None,
                         'provisional_packed': None,
                         'name': '65803',
                         'origin': 'N',
                         'source_type': 'N',
                         'source_subtype_1': 'N3',
                         'source_subtype_2': 'PH',
                         'elements_type': 'MPC_MINOR_PLANET',
                         'active': False,
                         'fast_moving': False,
                         'urgency': None,
                         'epochofel': datetime(2021, 2, 25, 0, 0),
                         'orbit_rms': 0.56,
                         'orbinc': 3.40768,
                         'longascnode': 73.20234,
                         'argofperih': 319.32035,
                         'eccentricity': 0.3836409,
                         'meandist': 1.6444571,
                         'meananom': 77.75787,
                         'perihdist': None,
                         'epochofperih': None,
                         'abs_mag': 18.27,
                         'slope': 0.15,
                         'score': None,
                         'discovery_date': datetime(1996, 4, 11, 0, 0),
                         'num_obs': 829,
                         'arc_length': 7305.0,
                         'not_seen': 2087.29154187494,
                         'updated': True,
                         'ingest': datetime(2018, 8, 14, 17, 45, 42),
                         'update_time': datetime(2021, 3, 1, 19, 59, 56, 957500)
                         }

        self.test_body, created = Body.objects.get_or_create(**body_params)

        block_params = {
                         'body' : self.test_body,
                         'request_number' : '12345',
                         'block_start' : datetime(2021, 10, 13, 0, 40),
                         'block_end' : datetime(2021, 10, 14, 0, 40),
                         'obstype' : Block.OPT_IMAGING,
                         'num_observed' : 1
                        }
        self.test_block, created = Block.objects.get_or_create(**block_params)
        # Second block with no frames attached
        block_params['num_observed'] = 0
        self.test_block2, created = Block.objects.get_or_create(**block_params)

        frame_params = {
                         'sitecode' : 'Z24',
                         'instrument' : 'fa11',
                         'filter' : 'ip',
                         'block' : self.test_block,
                         'frametype' : Frame.NEOX_RED_FRAMETYPE,
                         'zeropoint' : 27.0,
                         'zeropoint_err' : 0.03,
                         'midpoint' : block_params['block_start'] + timedelta(minutes=5),
                         'astrometric_catalog' : 'GAIA-DR2',
                         'photometric_catalog' : 'PANSTARRS',
                       }

        self.test_filenames = []
        for frame_num, frameid in zip(range(65,126,30),[45234032, 45234584, 45235052]):
            frame_params['filename'] = f"tfn1m001-fa11-20211013-{frame_num:04d}-e92.fits"
            frame_offset = frame_num-65
            frame_params['midpoint'] += timedelta(minutes=frame_offset)
            frame_params['frameid'] = frameid
            # Hand-rolled WCS
            naxis_header = {'NAXIS1' : 4096, 'NAXIS2' : 4096, 'NAXIS' : 2}
            w = WCS(naxis_header)
            w.wcs.crpix = [ 2048.0, 2048.0]
            pixel_scale = 0.389/3600.0
            w.wcs.cd = np.array([[pixel_scale, 0.0], [0.0, -pixel_scale]])
            w.wcs.crval = [270.01 + frame_offset*0.01, -27.02 - frame_offset*0.01]
            w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
            frame_params['wcs'] = w
            frame, created = Frame.objects.get_or_create(**frame_params)
            self.test_filenames.append(frame_params['filename'])

            mag_err = (frame_offset*0.0003) + 0.003
            source_params = { 'body' : self.test_body,
                              'frame' : frame,
                              'obs_ra' : 270 + frame_offset*0.01,
                              'obs_dec' : -27 - frame_offset*0.01,
                              'obs_mag' : 14.6 + frame_offset * 0.001,
                              'err_obs_ra' : 0.3/3600.0,
                              'err_obs_dec' : 0.3/3600.0,
                              'err_obs_mag' : mag_err,
                              'astrometric_catalog' : frame.astrometric_catalog,
                              'photometric_catalog' : frame.photometric_catalog,
                              'aperture_size' : 3.89,
                              'snr' : 1/mag_err,
                              'flags' : ''
                            }
            source, created = SourceMeasurement.objects.get_or_create(**source_params)

        self.maxDiff = None

    def test1(self):

        midpoints = Frame.objects.all().values_list('midpoint', flat=True)
        midpoints_jd = [Time(d).jd for d in midpoints]
        data_rows = [[self.test_filenames[0], midpoints_jd[0], 14.60, 0.03015, 27, 0.03, 14.60-27, 0.003, 'ip', 0, 10.0],
                     [self.test_filenames[1], midpoints_jd[1], 14.63, 0.03231, 27, 0.03, 14.63-27, 0.012, 'ip', 0, 10.0],
                     [self.test_filenames[2], midpoints_jd[2], 14.66, 0.03662, 27, 0.03, 14.66-27, 0.021, 'ip', 0, 10.0],
                    ]
        col_names = ['filename', 'julian_date', 'mag', 'sig', 'ZP', 'ZP_sig', 'inst_mag', 'in_sig', '[7]', '[8]', 'aprad']
        expected_table = Table(rows=data_rows, names=col_names)

        table = create_table_from_srcmeasures(self.test_block)

        self.assertEqual(len(expected_table), len(table))
        self.assertEqual(expected_table.colnames, table.colnames)
        for column in col_names:
            if expected_table[column].dtype.kind in ['U', 'S']:
                assert_array_equal(expected_table[column], table[column])
            else:
                assert_allclose(expected_table[column], table[column], rtol=1e-4, err_msg=f"Compare failure on column: {column}")


def make_synthetic_aper_table(num_epochs=30, cadence=210.0, t0_jd=2461233.875):
    """Builds a perform_aper_photometry()-style table for four simultaneous MuSCAT
    cameras with known colour offsets and a few deliberate defects:
      gp = rp + 0.55, ip = rp - 0.20, zs = rp - 0.15 (all within 0.1 mag of the S-type priors)
      zs frames start 64 s after rp and drift a further 1 s per frame
      ip frame at epoch 10 missing; gp frame at epoch 5 is a 0.5 mag outlier
      rp frame at epoch 20 unmeasured ("" values); rp frame at epoch 25 has a negative flux
    Returns (table, truth) with truth holding the offsets and per-band errors used."""

    rng = np.random.default_rng(42)
    offsets = {'rp': 0.0, 'gp': 0.55, 'ip': -0.20, 'zs': -0.15}
    errors = {'rp': 0.02, 'gp': 0.03, 'ip': 0.025, 'zs': 0.06}
    zp_sig = 0.01
    rows = []
    for obs_filter in ['gp', 'rp', 'ip', 'zs']:
        camera = {'gp': 'ep06', 'rp': 'ep07', 'ip': 'ep08', 'zs': 'ep09'}[obs_filter]
        for epoch in range(num_epochs):
            if obs_filter == 'ip' and epoch == 10:
                continue
            seconds = epoch * cadence + (64.0 + epoch if obs_filter == 'zs' else 0.0)
            jd = t0_jd + seconds / 86400.0
            mag = 20.2 + 0.1 * np.sin(2.0 * np.pi * seconds / 8640.0) + offsets[obs_filter] + rng.normal(0, errors[obs_filter])
            if obs_filter == 'gp' and epoch == 5:
                mag += 0.5
            zp = 24.8
            flux = 10**(-0.4 * (mag - zp))
            fname = f"/data/coj2m002-{camera}-20260712-{58 + epoch:04d}-e93.fits"
            row = [fname, Time(jd, format='jd').iso, obs_filter, 240.25, -22.24, 700.0, 1100.0,
                   flux, flux * errors[obs_filter] / 1.0857, 1.2, zp, zp_sig, mag, errors[obs_filter], 6.0, 1.608, 6.0, 0.268, 1.0857 / errors[obs_filter]]
            if obs_filter == 'rp' and epoch == 20:
                row = row[:3] + [""] * (len(row) - 3)
            elif obs_filter == 'rp' and epoch == 25:
                row[7] = -50.0
                row[12] = np.nan
            rows.append(row)
    names = ['path to frame', 'times', 'filters', 'RA', 'DEC', 'xcenter', 'ycenter', 'aperture sum', 'aperture sum err',
             'FWHM', 'ZP', 'ZP_sig', 'mag', 'magerr', 'aperture radius pix', 'aperture radius arcsec',
             'ZP aperture radius pix', 'pixel scale', 'SNR']
    # Column-wise so the "" row makes those columns strings, as perform_aper_photometry does
    columns = [[row[i] for row in rows] for i in range(len(names))]
    table = Table(columns, names=names)
    return table, {'offsets': offsets, 'errors': errors, 'zp_sig': zp_sig, 'cadence': cadence}


class TestExpectedColorOffsets(SimpleTestCase):

    def test_s_type_to_rp(self):
        offsets = expected_color_offsets('rp', 'S')

        self.assertEqual(0.0, offsets['rp'])
        self.assertAlmostEqual(0.600, offsets['gp'], 4)
        self.assertAlmostEqual(-0.195, offsets['ip'], 4)
        self.assertAlmostEqual(-0.141, offsets['zs'], 4)
        self.assertEqual(offsets['zs'], offsets['zp'])
        self.assertNotIn('B', offsets)

    def test_solar_to_gp(self):
        offsets = expected_color_offsets('gp', 'solar')

        self.assertEqual(0.0, offsets['gp'])
        self.assertAlmostEqual(-0.400, offsets['rp'], 4)

    def test_unknown_taxonomy_or_filter(self):
        self.assertEqual({}, expected_color_offsets('rp', 'Z'))
        self.assertEqual({}, expected_color_offsets('B', 'S'))

    def test_transform_Vmag_unchanged(self):
        from photometrics.photometry_subs import transform_Vmag

        self.assertAlmostEqual(20.0 - 0.275, transform_Vmag(20.0, 'r', 'S'), 6)
        self.assertAlmostEqual(20.0 + 0.217, transform_Vmag(20.0, 'g', 'solar'), 6)
        self.assertIsNone(transform_Vmag(20.0, 'B', 'S'))


class TestCombineSimultaneousBands(SimpleTestCase):

    def setUp(self):
        self.table, self.truth = make_synthetic_aper_table()
        self.combined, self.per_band, self.info = combine_simultaneous_bands(self.table)

    def test_epochs_and_band_counts(self):
        # Every rp epoch survives: the two unmeasurable rp frames are filled by the other bands
        self.assertEqual(30, len(self.combined))
        self.assertEqual(2, self.info['num_rows_removed'])
        nbands = list(self.combined['nbands'])
        self.assertEqual(26, nbands.count(4))
        self.assertEqual(4, nbands.count(3))
        self.assertEqual('riz', self.combined['bands'][5])      # gp outlier dropped (band order follows the table)
        self.assertEqual('grz', self.combined['bands'][10])     # ip frame missing
        self.assertEqual('giz', self.combined['bands'][20])     # rp frame unmeasured
        self.assertEqual('giz', self.combined['bands'][25])     # rp frame negative flux
        self.assertEqual({'gp': 0, 'rp': 0, 'ip': 0, 'zs': 0}, self.info['unmatched'])
        self.assertAlmostEqual(0.5 * self.truth['cadence'], self.info['match_tolerance_s'], 3)
        assert_array_equal(np.diff(self.combined['julian_date']) > 0, True)

    def test_outlier_flagged(self):
        gp = self.per_band['gp']
        self.assertEqual(1, gp['flag'].sum())
        self.assertTrue(gp['flag'][5])
        self.assertEqual(1, self.info['counts']['gp']['flagged'])
        self.assertEqual(29, self.info['counts']['gp']['used'])
        for obs_filter in ['rp', 'ip', 'zs']:
            self.assertEqual(0, self.per_band[obs_filter]['flag'].sum(), obs_filter)

    def test_offsets_recovered_and_priors_checked(self):
        for obs_filter, truth in self.truth['offsets'].items():
            self.assertAlmostEqual(truth, self.info['offsets'][obs_filter], delta=0.03, msg=obs_filter)
        self.assertEqual({'gp': False, 'ip': False, 'zs': False}, self.info['prior_mismatch'])
        self.assertEqual([], self.info['warnings'])
        self.assertAlmostEqual(0.600, self.info['priors']['gp'], 4)
        self.assertEqual(self.info['offsets'], self.combined.meta['offsets'])

    def test_prior_mismatch_flagged(self):
        _, _, info = combine_simultaneous_bands(self.table, color_priors={'gp': 0.0, 'ip': -0.2, 'zs': -0.15})

        self.assertTrue(info['prior_mismatch']['gp'])
        self.assertFalse(info['prior_mismatch']['ip'])
        self.assertEqual(1, len(info['warnings']))
        self.assertIn('gp', info['warnings'][0])
        # The fitted offset is still the one applied
        self.assertAlmostEqual(self.info['offsets']['gp'], info['offsets']['gp'], 6)

    def test_weighted_mean_and_error(self):
        epoch = 3
        mags, weights = [], []
        for obs_filter in ['gp', 'rp', 'ip', 'zs']:
            band = self.per_band[obs_filter]
            i = np.where(band['epoch'] == epoch)[0][0]
            self.assertAlmostEqual(np.sqrt(self.truth['errors'][obs_filter]**2 + self.truth['zp_sig']**2), band['err'][i], 6)
            mags.append(band['mag'][i] - self.info['offsets'][obs_filter])
            weights.append(1.0 / band['err'][i]**2)
        mags, weights = np.array(mags), np.array(weights)
        self.assertAlmostEqual(np.sum(weights * mags) / np.sum(weights), self.combined['mag'][epoch], 8)
        self.assertAlmostEqual(1.0 / np.sqrt(np.sum(weights)), self.combined['sig'][epoch], 8)
        self.assertEqual('coj2m002-ep07-20260712-0061-e93.fits', self.combined['filename'][epoch])
        self.assertEqual('rp', self.combined['[7]'][epoch])
        self.assertAlmostEqual(self.combined['mag'][epoch] - 24.8, self.combined['inst_mag'][epoch], 8)
        self.assertEqual(6.0, self.combined['aprad'][epoch])
        self.assertLess(self.combined['sig'][epoch], self.truth['errors']['rp'])

    def test_tight_tolerance_drops_zs(self):
        combined, _, info = combine_simultaneous_bands(self.table, match_tolerance=10.0 / 86400.0)

        # zs is 64+ s from every rp frame: no simultaneous pairs, so no colour offset can be
        # fitted and the band cannot be used. gp/ip still fill the two unmeasured rp epochs.
        self.assertEqual(0, info['unmatched']['zs'])
        self.assertEqual(0, info['counts']['zs']['used'])
        self.assertTrue(np.isnan(info['offsets']['zs']))
        self.assertEqual(1, len(info['warnings']))
        self.assertIn('zs', info['warnings'][0])
        self.assertEqual(30, len(combined))
        self.assertNotIn('z', ''.join(combined['bands']))
        self.assertEqual(30, info['counts']['gp']['used'] + 1)   # the outlier epoch

    def test_min_bands(self):
        combined, _, _ = combine_simultaneous_bands(self.table, min_bands=4)

        self.assertEqual(26, len(combined))
        assert_array_equal(combined['nbands'], 4)

    def test_single_band_table(self):
        rp_only = self.table[self.table['filters'] == 'rp']
        combined, per_band, info = combine_simultaneous_bands(rp_only)

        self.assertEqual(28, len(combined))
        self.assertEqual(['rp'], info['filters'])
        assert_array_equal(combined['nbands'], 1)
        assert_allclose(combined['mag'], per_band['rp']['mag'])
        assert_allclose(combined['sig'], per_band['rp']['err'])

    def test_missing_reference_filter(self):
        with self.assertRaises(ValueError):
            combine_simultaneous_bands(self.table, ref_filter='w')


class TestBinLightcurve(SimpleTestCase):

    def test_bin_pairs(self):
        table = Table({'julian_date': [1.0, 2.0, 3.0, 4.0, 5.0], 'mag': [20.0, 20.2, 20.4, 20.6, 20.8],
                       'sig': [0.1, 0.1, 0.1, 0.3, 0.1], 'nbands': [4, 3, 4, 4, 2], 'bands': ['griz', 'grz', 'griz', 'griz', 'gr']})

        binned = bin_lightcurve(table, nbin=2)

        self.assertEqual(2, len(binned))
        assert_allclose(binned['julian_date'], [1.5, 3.5])
        self.assertAlmostEqual(20.1, binned['mag'][0], 8)
        self.assertAlmostEqual((20.4 / 0.01 + 20.6 / 0.09) / (1 / 0.01 + 1 / 0.09), binned['mag'][1], 8)
        self.assertAlmostEqual(0.1 / np.sqrt(2.0), binned['sig'][0], 8)
        assert_array_equal(binned['nbands'], [7, 8])
        assert_array_equal(binned['bands'], ['grizgrz', 'grizgriz'])

    def test_too_short(self):
        table = Table({'julian_date': [1.0], 'mag': [20.0], 'sig': [0.1]})

        binned = bin_lightcurve(table, nbin=2)

        self.assertEqual(0, len(binned))
        self.assertEqual(['julian_date', 'mag', 'sig'], binned.colnames)


class TestAperTableToDartTable(SimpleTestCase):

    def setUp(self):
        self.table, self.truth = make_synthetic_aper_table()
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_columns(self):
        dart = aper_table_to_dart_table(self.table, 'rp')

        self.assertEqual(28, len(dart))
        self.assertEqual(['filename', 'julian_date', 'mag', 'sig', 'ZP', 'ZP_sig', 'inst_mag', 'in_sig', '[7]', '[8]', 'aprad'], dart.colnames)
        self.assertEqual('coj2m002-ep07-20260712-0058-e93.fits', dart['filename'][0])
        self.assertAlmostEqual(np.sqrt(0.02**2 + 0.01**2), dart['sig'][0], 8)
        self.assertEqual(0.02, dart['in_sig'][0])
        self.assertAlmostEqual(dart['mag'][0] - 24.8, dart['inst_mag'][0], 8)
        assert_array_equal(dart['[7]'], 'rp')
        assert_array_equal(dart['[8]'], 0)
        assert_array_equal(np.diff(dart['julian_date']) > 0, True)

    def test_round_trip_dart_file(self):
        dart = aper_table_to_dart_table(self.table, 'ip')
        filepath = os.path.join(self.test_dir, 'ip_dart.txt')

        write_dartformat_file(dart, filepath, aprad=6.0)
        with open(filepath) as fh:
            lines = fh.readlines()

        self.assertEqual(30, len(lines))
        self.assertEqual('file julian_date mag sig ZP ZP_sig inst_mag inst_sig filter SExtractor_flag aprad', ' '.join(lines[0].split()))
        fields = lines[1].split()
        self.assertEqual('coj2m002-ep08-20260712-0058-e93.fits', fields[0])
        self.assertEqual(f"{dart['julian_date'][0]:.7f}", fields[1])
        self.assertEqual('ip', fields[8])
        self.assertEqual('6.00', fields[10])

        with self.assertRaises(OSError):
            write_dartformat_file(dart, filepath, aprad=6.0)
        write_dartformat_file(dart, filepath, aprad=6.0, overwrite=True)
