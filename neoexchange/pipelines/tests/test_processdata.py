import numpy as np
from astropy.coordinates import SkyCoord
from astropy.table import Table
from django.test import SimpleTestCase
from numpy.ma import masked_array
from numpy.testing import assert_allclose

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
