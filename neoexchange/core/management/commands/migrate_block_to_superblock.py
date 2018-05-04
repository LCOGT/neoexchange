from django.core.management.base import BaseCommand, CommandError

from core.models import Block, SuperBlock

class Command(BaseCommand):

    help = 'Management command to copy Block information into SuperBlock'

    def handle(self, *args, **options):

        blocks = Block.objects.all()
        msg = "Found %d Blocks to migrate" % (blocks.count())
        self.stdout.write(msg)

	printcounter = 0
        for block in blocks:
	    if printcounter % 100==0:
		print("Migrated Block #%d" % printcounter)
            cadence = False
            if 'cad' in block.groupid:
                cadence = True
            # Call overloaded save method to create SuperBlock
            block.save()
            block.superblock.cadence = cadence
            block.superblock.save()
	    printcounter += 1
