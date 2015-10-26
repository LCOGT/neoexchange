from core.models import Block
from django.core.management.base import BaseCommand, CommandError
from datetime import datetime
from core.views import block_status

class Command(BaseCommand):
    help = 'Update pending blocks if observation requests have been made'

    def handle(self, *args, **options):
        blocks = Block.objects.filter(active=True, block_start__lte=datetime.now(), block_end__lte=datetime.now())
        self.stdout.write("==== %s Active Blocks in current horizon %s ====" % (blocks.count(), datetime.now().strftime('%Y-%m-%d %H:%M')))
        for block in blocks:
            block_status(block.id)
        inconsistent_blocks = Block.objects.filter(active=True, block_end__lt=datetime.utcnow())
        self.stdout.write("==== Clean up %s blocks ====" % inconsistent_blocks.count())
        inconsistent_blocks.update(active=False)
