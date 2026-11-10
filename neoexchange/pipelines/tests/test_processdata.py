from unittest.mock import patch

import numpy as np
from astropy.coordinates import SkyCoord
from astropy.table import Table
from django.test import SimpleTestCase, TestCase
from numpy.ma import masked_array
from numpy.testing import assert_allclose

from core.models.async_process import AsyncError
from core.utils import NeoException


class EmptyRefCat:
    """Stands in for a calviacat Catalog whose fetch_field() silently fails (e.g.
    the catalog service is down), leaving nothing to search."""

    def __init__(self):
        self.num_fetches = 0

    def search(self, sources):
        return [], SkyCoord([], [], unit='deg')

    def fetch_field(self, sources):
        self.num_fetches += 1


class TestCrossMatchAndZp(SimpleTestCase):

    def setUp(self):
        # Imported here, not at module level: the pipeline proxy models register in an app without
        # migrations, which breaks test database creation if they exist before the DB is set up
        from pipelines.processdata import ZeropointProcessPipeline

        self.table = Table({'flags': [0, 0, 0],
                            'obs_ra': [240.20, 240.21, 240.22],
                            'obs_dec': [-22.20, -22.21, -22.22],
                            'obs_mag': [15.0, 16.0, 17.0]})
        self.pipeline = ZeropointProcessPipeline()

    def test_empty_catalog_after_fetch_fails_the_step(self):
        refcat = EmptyRefCat()

        with self.assertRaisesRegex(NeoException, 'No EmptyRefCat sources after fetching field'):
            self.pipeline.cross_match_and_zp(self.table, refcat, 0.1, 'r', 'rp')
        self.assertEqual(1, refcat.num_fetches)


class RecordingRefCat:
    """Stands in for a calviacat Catalog whose field is already fetched; records the
    instrumental magnitudes handed to the calibration."""

    def __init__(self):
        self.inst_mag = None

    def search(self, sources):
        return [0] * 500, SkyCoord([0.0] * 500, [0.0] * 500, unit='deg')

    def fetch_field(self, sources):
        raise AssertionError('fetch_field() should not be called when the field is populated')

    def xmatch(self, sources):
        return np.arange(len(sources)), np.zeros(len(sources))

    def cal_constant(self, objids, inst_mag, cal_filter, gmi_lim=None):
        self.inst_mag = np.array(inst_mag)
        r = masked_array([0.0] * len(objids), mask=[False] * len(objids))
        return 24.5, 0.0, 0.05, r, r


class TestCrossMatchAndZpMultiAperture(SimpleTestCase):
    """obs_mag from a multi-aperture catalog is (N, num_apertures): one column per PHOT_APERTURES
    entry. The caller says which column to fit (ZeropointProcessPipeline.do_pipeline reads it from
    the SExtractor config beside the catalog)."""

    def setUp(self):
        from pipelines.processdata import ZeropointProcessPipeline

        self.table = Table({'flags': [0, 0, 0],
                            'obs_ra': [240.20, 240.21, 240.22],
                            'obs_dec': [-22.20, -22.21, -22.22],
                            'obs_mag': [[m + 0.1 * i for i in range(11)] for m in (15.0, 16.0, 17.0)]})
        self.pipeline = ZeropointProcessPipeline()
        self.refcat = RecordingRefCat()

    def test_fits_the_given_aperture(self):
        results = self.pipeline.cross_match_and_zp(self.table, self.refcat, 0.1, 'r', 'rp', zp_aperture_index=4)

        assert_allclose([15.4, 16.4, 17.4], self.refcat.inst_mag)
        self.assertEqual((24.5, 0.05, 0.0, 'g-i'), results)

    def test_fits_another_aperture(self):
        self.pipeline.cross_match_and_zp(self.table, self.refcat, 0.1, 'r', 'rp', zp_aperture_index=2)

        assert_allclose([15.2, 16.2, 17.2], self.refcat.inst_mag)

    def test_multi_aperture_needs_an_index(self):
        with self.assertRaisesRegex(NeoException, 'no zeropoint aperture index'):
            self.pipeline.cross_match_and_zp(self.table, self.refcat, 0.1, 'r', 'rp')
        self.assertIsNone(self.refcat.inst_mag)

    def test_single_aperture_ignores_the_index(self):
        table = Table({'flags': [0, 0, 0], 'obs_ra': [240.20, 240.21, 240.22],
                       'obs_dec': [-22.20, -22.21, -22.22], 'obs_mag': [15.0, 16.0, 17.0]})

        results = self.pipeline.cross_match_and_zp(table, self.refcat, 0.1, 'r', 'rp', zp_aperture_index=4)

        assert_allclose([15.0, 16.0, 17.0], self.refcat.inst_mag)
        self.assertEqual((24.5, 0.05, 0.0, 'g-i'), results)


class TestSExtractorProcessPipelineFailures(TestCase):
    """proc-extract must record a failure when SExtractor does not run (for
    example because the config setup failed), rather than completing and
    leaving every later step of the chain to fail on the missing catalog."""

    def setUp(self):
        # Imported here, not at module level: importing the proxy models before the
        # test database is built breaks the migration state (no pipelines migrations)
        from pipelines.processdata import SExtractorProcessPipeline
        self.cls = SExtractorProcessPipeline
        self.inputs = {f: self.cls.inputs[f]['default'] for f in self.cls.inputs}
        self.inputs.update({'fits_file': '/data/20260712/coj2m002-ep08-20260712-0109-e91.fits',
                            'datadir': '/data/Hera/20260712/'})
        self.pipe = self.cls.create_timestamped(self.inputs)

    def test_sextractor_failure_raises(self):
        with patch.object(self.cls, 'setup', return_value=self.inputs['fits_file']), \
             patch.object(self.cls, 'process', return_value=-4), \
             self.assertRaises(AsyncError) as cm:
            self.pipe.do_pipeline('/tmp', **self.inputs)

        self.assertEqual("SExtractor failed on coj2m002-ep08-20260712-0109-e91.fits (status -4)", str(cm.exception))

    def test_missing_image_raises(self):
        with patch.object(self.cls, 'setup', return_value=-1), \
             patch.object(self.cls, 'process') as process, \
             self.assertRaises(AsyncError) as cm:
            self.pipe.do_pipeline('/tmp', **self.inputs)

        process.assert_not_called()
        self.assertEqual("No image found for coj2m002-ep08-20260712-0109-e91.fits (status -1)", str(cm.exception))

    def test_existing_catalog_completes(self):
        with patch.object(self.cls, 'setup', return_value=0), \
             patch.object(self.cls, 'process') as process:
            self.pipe.do_pipeline('/tmp', **self.inputs)

        process.assert_not_called()
        self.assertIn('Pipeline Completed', self.pipe.logs)

    def test_run_reports_failure(self):
        with patch.object(self.cls, 'setup', return_value=self.inputs['fits_file']), \
             patch.object(self.cls, 'process', return_value=-4), \
             self.assertRaises(AsyncError) as cm:
            self.pipe.run()

        self.assertIn("SExtractor failed on coj2m002-ep08-20260712-0109-e91.fits (status -4)", str(cm.exception))



class TestScampProcessPipelineRmsWarning(TestCase):
    """proc-astromfit warns when a nominally good fit has a reference RMS that is
    too large for 1m0/2m0 data against Gaia (the symptom of a reference catalog
    not at the epoch of observation)."""

    def setUp(self):
        # Imported here, not at module level: see TestSExtractorProcessPipelineFailures
        from pipelines.processdata import ScampProcessPipeline
        self.cls = ScampProcessPipeline
        self.inputs = {f: self.cls.inputs[f]['default'] for f in self.cls.inputs}
        self.inputs.update({'fits_file': '/data/20260712/coj2m002-ep07-20260712-0063-e91.fits',
                            'datadir': '/data/Hera/20260712/'})
        self.pipe = self.cls.create_timestamped(self.inputs)
        self.fits_file = '/data/Hera/20260712/coj2m002-ep07-20260712-0063-e92.fits'
        self.header = {'astrometric_fit_status': 0,
                       'astrometric_fit_rms': 0.17,
                       'astrometric_catalog': 'GAIA-DR3',
                       'astrometric_epoch': None}

    def test_high_rms_warns(self):
        # Patch the module logger rather than assertLogs(): other test modules disable logging
        with patch('pipelines.processdata.logger') as mock_logger:
            warned = self.pipe.check_fit_rms(self.header, self.fits_file)

        self.assertTrue(warned)
        mock_logger.warning.assert_called_once()
        self.assertIn('exceeds 0.1"', mock_logger.warning.call_args[0][0])
        self.assertIn('RMS of 0.170" for coj2m002-ep07-20260712-0063-e92.fits against GAIA-DR3', self.pipe.logs)
        self.assertIn('WCSREPOC=None', self.pipe.logs)

    def test_good_rms_is_quiet(self):
        self.header['astrometric_fit_rms'] = 0.03
        self.header['astrometric_epoch'] = 2026.5271

        warned = self.pipe.check_fit_rms(self.header, self.fits_file)

        self.assertFalse(warned)
        self.assertNotIn('exceeds', self.pipe.logs or '')

    def test_bad_fit_is_quiet(self):
        # A failed fit (status 5, rms None) is reported elsewhere
        self.header['astrometric_fit_status'] = 5
        self.header['astrometric_fit_rms'] = None

        warned = self.pipe.check_fit_rms(self.header, self.fits_file)

        self.assertFalse(warned)
        self.assertNotIn('exceeds', self.pipe.logs or '')
