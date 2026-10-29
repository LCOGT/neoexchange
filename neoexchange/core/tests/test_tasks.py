from unittest.mock import patch

from django.test import TestCase

from core.models.async_process import ASYNC_STATUS_FAILED, ASYNC_STATUS_PENDING, AsyncError, AsyncProcess
from core.tasks import run_process


class TestRunProcess(TestCase):

    def setUp(self):
        self.process = AsyncProcess.objects.create(identifier='run_process__1')
        self.max_length = AsyncProcess._meta.get_field('failure_message').max_length

    def test_short_failure_message_stored_verbatim(self):
        with patch.object(AsyncProcess, 'run', side_effect=AsyncError('Error performing zeropoint determination')):
            result = run_process(self.process)

        self.process.refresh_from_db()
        self.assertEqual('Error performing zeropoint determination', result)
        self.assertEqual(ASYNC_STATUS_FAILED, self.process.status)
        self.assertEqual('Error performing zeropoint determination', self.process.failure_message)

    def test_long_failure_message_is_truncated_and_process_marked_failed(self):
        message = ("HTTPSConnectionPool(host='vizier.cds.unistra.fr', port=443): Max retries exceeded with url: "
                   "/viz-bin/votable (Caused by ConnectTimeoutError(<urllib3.connection.HTTPSConnection object at "
                   "0x7f2ba2eaa0a0>, 'Connection to vizier.cds.unistra.fr timed out. (connect timeout=120)'))")
        self.assertGreater(len(message), self.max_length)

        with patch.object(AsyncProcess, 'run', side_effect=AsyncError(message)):
            result = run_process(self.process)

        self.process.refresh_from_db()
        self.assertEqual(ASYNC_STATUS_FAILED, self.process.status)
        self.assertIsNotNone(self.process.terminal_timestamp)
        self.assertEqual(self.max_length, len(self.process.failure_message))
        self.assertTrue(self.process.failure_message.startswith("HTTPSConnectionPool(host='vizier.cds.unistra.fr'"))
        self.assertTrue(self.process.failure_message.endswith('...'))
        self.assertEqual(self.process.failure_message, result)

    def test_successful_run_leaves_status_alone(self):
        with patch.object(AsyncProcess, 'run', return_value=None):
            result = run_process(self.process)

        self.process.refresh_from_db()
        self.assertEqual('process finished', result)
        self.assertEqual(ASYNC_STATUS_PENDING, self.process.status)
        self.assertEqual('', self.process.failure_message)
