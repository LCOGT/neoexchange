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
from unittest.mock import MagicMock, PropertyMock, patch

from django.core.management import call_command
from django.test import TestCase

from core.models import Block, Body, Frame, Proposal, SuperBlock


class TestMakeSubtractionsFilename(TestCase):
    """make_subtractions picks its science frames by globbing the data directory for
    '<rootname>*e92.fits', so the Block's own frames and any other e92s with the same
    rootname (other Blocks from the same night) are all passed to the subtraction.
    --filename narrows that list to one frame."""

    e92_names = ('coj2m002-ep08-20260717-0001-e92.fits',    # another Block, same night and rootname
                 'coj2m002-ep08-20260717-0062-e92.fits',
                 'coj2m002-ep08-20260717-0063-e92.fits',
                 'coj2m002-ep08-20260717-0064-e92.fits')

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')
        self.data_dir = os.path.join(self.test_dir, 'Hera', '20260717', '')
        os.makedirs(self.data_dir)
        for name in self.e92_names:
            open(os.path.join(self.data_dir, name), 'w').close()

        body = Body.objects.create(provisional_name='Didymos', name='65803', origin='M', source_type='N', active=True)
        proposal = Proposal.objects.create(code='LCOTest', title='test', pi='bart.simpson@lcogt.net', tag='LCOGT', active=True)
        sblock = SuperBlock.objects.create(body=body, proposal=proposal, groupid='Didymos_COJ_2026_Field#11',
                                           block_start='2026-07-17 08:00:00', block_end='2026-07-17 12:00:00',
                                           tracking_number='00042', active=True)
        self.block = Block.objects.create(telclass='2m0', site='COJ', body=body, superblock=sblock,
                                          block_start='2026-07-17 08:00:00', block_end='2026-07-17 12:00:00',
                                          request_number='4272067', num_exposures=100, exp_length=60.0,
                                          num_observed=1, active=True)
        frame_params = {'sitecode': 'E10', 'instrument': 'ep08', 'filter': 'rp', 'exptime': 60.0, 'block': self.block}
        for i, name in enumerate(self.e92_names[1:]):
            Frame.objects.create(filename=name, frametype=Frame.NEOX_RED_FRAMETYPE,
                                 midpoint=datetime(2026, 7, 17, 10, i, 0), **frame_params)

        self.ref_frame = os.path.join(self.test_dir, 'reference_library', 'reference_COJ_ep08_rp.fits')
        field = MagicMock()
        field.current_name.return_value = 'Didymos'
        self.patchers = [
            patch('core.management.commands.make_subtractions.determine_reffield_for_block', return_value=field),
            patch('core.management.commands.make_subtractions.determine_reference_frame_for_block', return_value=self.ref_frame),
            patch('core.management.commands.make_subtractions.run_hotpants_subtraction', return_value=0),
            patch.object(Block, 'get_blockdayobs', new_callable=PropertyMock, return_value='20260717'),
        ]
        for patcher in self.patchers:
            started = patcher.start()
            if patcher.attribute == 'run_hotpants_subtraction':
                self.mock_hotpants = started

    def tearDown(self):
        for patcher in reversed(self.patchers):
            patcher.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def run_command(self, *extra_args):
        out = StringIO()
        with self.settings(DATA_ROOT=self.test_dir):
            call_command('make_subtractions', '4272067', self.data_dir, '--execute', *extra_args, stdout=out)
        return out.getvalue()

    def subtracted_files(self):
        self.assertEqual(1, self.mock_hotpants.call_count)
        return [os.path.basename(f) for f in self.mock_hotpants.call_args.args[4]]

    def test_without_filename_all_e92s_with_rootname_are_subtracted(self):
        output = self.run_command()

        self.assertEqual(list(self.e92_names), self.subtracted_files())
        self.assertIn('Found 4 e92 frames with correct rootname', output)

    def test_filename_selects_single_frame(self):
        output = self.run_command('--filename', 'coj2m002-ep08-20260717-0063')

        self.assertEqual(['coj2m002-ep08-20260717-0063-e92.fits'], self.subtracted_files())
        self.assertIn('Found 1 e92 frames with correct rootname', output)

    def test_filename_with_no_match_skips_subtraction(self):
        output = self.run_command('--filename', 'coj2m002-ep08-20260717-9999')

        self.mock_hotpants.assert_not_called()
        self.assertIn("No e92 frames matching 'coj2m002-ep08-20260717-9999' found in", output)
