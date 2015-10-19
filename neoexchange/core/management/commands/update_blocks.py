from core.models import Block
from django.core.management.base import BaseCommand, CommandError
from datetime import datetime

class Command(BaseCommand):
    help = 'Update pending blocks if observation requests have been made'

    def handle(self, *args, **options):
        blocks = Block.objects.filter(active=True, block_start__lte=datetime.now(), block_end__lte=datetime.now())
        self.stdout.write("==== %s Active Blocks in current horizon %s ====" % (blocks.count(), datetime.now().strftime('%Y-%m-%d %H:%M')))
