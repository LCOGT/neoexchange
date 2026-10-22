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
    """obs_mag from a sextractor_neox_ldac_multiaper.conf catalog is (N, 11): one column per
    PHOT_APERTURES entry (5.13..51.33 px diameter)."""

    def setUp(self):
        from pipelines.processdata import ZeropointProcessPipeline

        self.table = Table({'flags': [0, 0, 0],
                            'obs_ra': [240.20, 240.21, 240.22],
                            'obs_dec': [-22.20, -22.21, -22.22],
                            'obs_mag': [[m + 0.1 * i for i in range(11)] for m in (15.0, 16.0, 17.0)]})
        self.pipeline = ZeropointProcessPipeline()
        self.refcat = RecordingRefCat()

    def test_fit_uses_fifth_aperture(self):
        self.pipeline.cross_match_and_zp(self.table, self.refcat, 0.1, 'r', 'rp')

        assert_allclose([15.4, 16.4, 17.4], self.refcat.inst_mag)

    def test_returns_the_aperture_radius_it_fitted(self):
        # index 4 of the aperture list: 22.00 px diameter = 11.0 px radius. SEXAPED1-4 cannot
        # record it, so the stage reports it for update_zeropoint() to write L1ZPAPER.
        avg_zp, std_zp, C, cal_color, zp_aperture_pix = self.pipeline.cross_match_and_zp(self.table, self.refcat, 0.1, 'r', 'rp')

        self.assertEqual((24.5, 0.05, 0.0, 'g-i'), (avg_zp, std_zp, C, cal_color))
        self.assertAlmostEqual(11.0, zp_aperture_pix, places=5)

    def test_single_aperture_reports_no_radius(self):
        table = Table({'flags': [0, 0, 0], 'obs_ra': [240.20, 240.21, 240.22],
                       'obs_dec': [-22.20, -22.21, -22.22], 'obs_mag': [15.0, 16.0, 17.0]})

        *_, zp_aperture_pix = self.pipeline.cross_match_and_zp(table, self.refcat, 0.1, 'r', 'rp')

        self.assertIsNone(zp_aperture_pix)
        assert_allclose([15.0, 16.0, 17.0], self.refcat.inst_mag)
