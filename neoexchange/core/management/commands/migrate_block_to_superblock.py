from django.core.management.base import BaseCommand, CommandError

from core.models import Block, SuperBlock

class Command(BaseCommand):

    help = 'Management command to copy Block information into SuperBlock'

    def handle(self, *args, **options):

        blocks = Block.objects.all()
        
        for block in blocks:
            cadence = False
            if 'cad' in block.groupid:
                cadence = True
            # Call overloaded save method to create SuperBlock
            block.save()
            block.superblock.cadence = cadence
            block.superblock.save()
