from core.models import Block, SuperBlock
from django.core.management.base import BaseCommand, CommandError
from datetime import datetime, timedelta
from core.frames import block_status

class Command(BaseCommand):
    help = 'Update pending blocks if observation requests have been made'

    def handle(self, *args, **options):
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
            num_active_block = Blocks.objects.filter(superblock=sblock.id, active=True).count()
            if num_active_blocks == 0:
                sblock.active = False
                sblock.save()

        # Check for Blocks and SuperBlocks whose end time is more than 2 hours
        # ago and set them inactive
        inconsistent_blocks = Block.objects.filter(active=True, block_end__lt=now-timedelta(minutes=120))
        self.stdout.write("==== Clean up %s blocks ====" % inconsistent_blocks.count())
        inconsistent_blocks.update(active=False)
        completed_sblocks = SuperBlock.objects.filter(active=True, block_end__lt=now-timedelta(minutes=120))
        self.stdout.write("==== Clean up %s SuperBlocks ====" % completed_sblocks.count())
        completed_sblocks.update(active=False)
