from io import StringIO

from django.test import TestCase

from core.models.async_process import ASYNC_STATUS_CREATED, ASYNC_STATUS_FAILED


class TestRunPipelineSummarize(TestCase):

    def setUp(self):
        # Imported here, not at module level: the pipeline proxy models register in an app without
        # migrations, which breaks test database creation if they exist before the DB is set up
        from core.management.commands.run_pipeline import Command
        from pipelines.processdata import ScampProcessPipeline, ZeropointProcessPipeline

        self.ScampProcessPipeline = ScampProcessPipeline
        self.ZeropointProcessPipeline = ZeropointProcessPipeline
        self.stdout = StringIO()
        self.command = Command(stdout=self.stdout)

    def test_tallies_statuses_and_lists_failures(self):
        ScampProcessPipeline, ZeropointProcessPipeline = self.ScampProcessPipeline, self.ZeropointProcessPipeline
        ok_fit = ScampProcessPipeline.objects.create(identifier='scamp__1', status=ASYNC_STATUS_CREATED)
        ok_zp = ZeropointProcessPipeline.objects.create(identifier='zp__1', status=ASYNC_STATUS_CREATED)
        bad_zp = ZeropointProcessPipeline.objects.create(identifier='zp__2', status=ASYNC_STATUS_FAILED,
                                                         failure_message='Error performing zeropoint determination')
        pending_zp = ZeropointProcessPipeline.objects.create(identifier='zp__3')
        processes = [('frame-0001-e91.fits', 'proc-astromfit', ok_fit.pk),
                     ('frame-0001-e91.fits', 'proc-zeropoint', ok_zp.pk),
                     ('frame-0002-e91.fits', 'proc-zeropoint', bad_zp.pk),
                     ('frame-0003-e91.fits', 'proc-zeropoint', pending_zp.pk)]

        num_failures = self.command.summarize(processes)

        self.assertEqual(2, num_failures)
        output = self.stdout.getvalue()
        self.assertIn('proc-astromfit : 1 complete\n', output)
        self.assertIn('proc-zeropoint : 1 complete, 1 failed, 1 pending\n', output)
        self.assertIn('2 steps did not complete', output)
        self.assertIn('frame-0002-e91.fits proc-zeropoint: failed Error performing zeropoint determination\n', output)
        self.assertIn('frame-0003-e91.fits proc-zeropoint: pending\n', output)
        self.assertNotIn('frame-0001', output.split('did not complete')[1])

    def test_all_complete_lists_nothing(self):
        ok_zp = self.ZeropointProcessPipeline.objects.create(identifier='zp__1', status=ASYNC_STATUS_CREATED)

        num_failures = self.command.summarize([('frame-0001-e91.fits', 'proc-zeropoint', ok_zp.pk)])

        self.assertEqual(0, num_failures)
        self.assertNotIn('did not complete', self.stdout.getvalue())
