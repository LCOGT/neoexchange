from django.test import SimpleTestCase


class TestPipelineImports(SimpleTestCase):
    """Nothing else in the suite imports the pipeline modules, so a broken import
    (e.g. after moving a helper between modules) would otherwise only show up
    when a pipeline runs."""

    def test_import_pipeline_modules(self):
        from pipelines import downloaddata, ephemeris, processdata

        for name in ('find_block_for_frame', 'update_frame_zeropoint', 'make_new_catalog_entry'):
            with self.subTest(name=name):
                self.assertTrue(callable(getattr(processdata, name)))
        self.assertTrue(downloaddata and ephemeris)
