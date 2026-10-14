from astropy.coordinates import SkyCoord
from astropy.table import Table
from django.test import SimpleTestCase

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
