"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2017-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

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
