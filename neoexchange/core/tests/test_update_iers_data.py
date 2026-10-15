"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2026 LCO

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
from io import StringIO

from astropy.utils import iers
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase
from mock import patch

from astrometrics.time_subs import IERS_A_URL


@patch('core.management.commands.update_iers_data.import_file_to_cache')
@patch('core.management.commands.update_iers_data.download_file')
class TestUpdateIERSData(SimpleTestCase):

    iers_fixture = os.path.join(os.path.dirname(__file__), '..', '..', 'astrometrics', 'tests', 'iers', 'finals2000A_truncated.all')
    sources = [IERS_A_URL, iers.conf.iers_auto_url_mirror]

    def test_download_and_cache(self, mock_download, mock_import):
        mock_download.return_value = self.iers_fixture
        out = StringIO()

        call_command('update_iers_data', stdout=out)

        mock_download.assert_called_once_with(IERS_A_URL, sources=self.sources, cache=False)
        mock_import.assert_called_once_with(IERS_A_URL, self.iers_fixture, remove_original=True)
        self.assertIn('Cached IERS-A table with 100 rows: MJD 61272-61371, predictions from MJD 61322', out.getvalue())

    def test_download_failure_leaves_cache_alone(self, mock_download, mock_import):
        mock_download.side_effect = OSError('<urlopen error timed out>')

        with self.assertRaises(CommandError) as cm:
            call_command('update_iers_data', stdout=StringIO())

        self.assertIn('timed out', str(cm.exception))
        self.assertIn(iers.conf.iers_auto_url_mirror, str(cm.exception))
        mock_import.assert_not_called()

    def test_bad_download_leaves_cache_alone(self, mock_download, mock_import):
        mock_download.return_value = __file__

        with self.assertRaises(CommandError):
            call_command('update_iers_data', stdout=StringIO())

        mock_import.assert_not_called()
