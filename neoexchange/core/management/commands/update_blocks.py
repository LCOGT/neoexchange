"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2015-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from core.models import Block, SuperBlock
from django.core.management.base import BaseCommand, CommandError
from datetime import datetime, timedelta
from core.frames import block_status


class Command(BaseCommand):
    help = 'Update pending blocks if observation requests have been made'

    def handle(self, *args, **options):
        delta = 240
        now = datetime.utcnow()
        now_string = now.strftime('%Y-%m-%d %H:%M')
        blocks = Block.objects.filter(active=True, block_start__lte=now, block_end__lte=now)
        self.stdout.write("==== %s Completed Blocks %s ====" % (blocks.count(), now_string))
        for block in blocks:
            block_status(block.id)
        blocks = Block.objects.filter(active=True, block_start__lte=now, block_end__gte=now)
        self.stdout.write("==== %s Currently Executing Blocks %s ====" % (blocks.count(), now_string))
        for block in blocks:
            block_status(block.id)
        # Check for SuperBlocks whose end time has past. If all their sub-Blocks
        # are no longer active, set the superblock to inactive
        superblocks = SuperBlock.objects.filter(active=True, block_start__lte=now, block_end__lte=now)
        self.stdout.write("==== %s Completed SuperBlocks %s ====" % (superblocks.count(), now_string))
        for sblock in superblocks:
            num_active_blocks = Block.objects.filter(superblock=sblock.id, active=True).count()
            if num_active_blocks == 0:
                sblock.active = False
                sblock.save()

        # Check for Blocks and SuperBlocks whose end time is more than delta minutes ago
        # ago and set them inactive
        inconsistent_blocks = Block.objects.filter(active=True, block_end__lt=now-timedelta(minutes=delta))
        delta_dt = now-timedelta(minutes=delta)
        delta_string = delta_dt.strftime("%Y-%m-%d %H:%M")
        self.stdout.write("==== Clean up %s blocks more than %s mins old (%s)====" % (inconsistent_blocks.count(), delta, delta_string))
        inconsistent_blocks.update(active=False)
        completed_sblocks = SuperBlock.objects.filter(active=True, block_end__lt=now-timedelta(minutes=delta))
        self.stdout.write("==== Clean up %s SuperBlocks more than %s mins old (%s) ====" % (completed_sblocks.count(), delta, delta_string))
        completed_sblocks.update(active=False)

        # Double check for late arrivals 12 and 24 hours after block end.
        # WARNING: Rolling 20 minute check at 12 and 24 hours is based on the 20 minute crontab cadence for running update_blocks
        blocks = Block.objects.filter(block_end__gte=now-timedelta(hours=12)-timedelta(minutes=20), block_end__lte=now-timedelta(hours=12))
        self.stdout.write("==== Check %s blocks that ended 12 hours ago for incomplete download %s ====" % (blocks.count(), now_string))
        for block in blocks:
            block_status(block.id)
        blocks = Block.objects.filter(block_end__gte=now-timedelta(hours=24)-timedelta(minutes=20), block_end__lte=now-timedelta(hours=24))
        self.stdout.write("==== Check %s blocks that ended 24 hours ago for incomplete download %s ====" % (blocks.count(), now_string))
        for block in blocks:
            block_status(block.id)
