import os
from sys import exit
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.forms.models import model_to_dict

from core.models import Block, Frame
from astrometrics.ephem_subs import compute_ephem, radec2strings
from photometrics.catalog_subs import search_box

class Command(BaseCommand):

    help = 'Extract lightcurves of a target from a given Block'

    def add_arguments(self, parser):
        parser.add_argument('blocknum', type=int, help='Block number to analyze')

    def handle(self, *args, **options):

        self.stdout.write("==== Light curve building %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))

        try:
            block = Block.objects.get(id=options['blocknum'])
        except Block.DoesNotExist:
            self.stdout.write("Cannot find Block# %d" % options['blocknum'])
            exit(-1)
        
        self.stdout.write("Analyzing Block# %d for %s" % (block.id, block.body.current_name()))

        frames = Frame.objects.filter(block=block.id, zeropoint__isnull=False)
        self.stdout.write("Found %d frames for Block# %d with good ZPs" % (len(frames), block.id))
        if len(frames) != 0:
            elements = model_to_dict(block.body)

            for frame in frames:
                emp_line = compute_ephem(frame.midpoint, elements, frame.sitecode)
                (ra_string, dec_string) = radec2strings(emp_line[1], emp_line[2], ' ')
                sources = search_box(frame, emp_line[1], emp_line[2], 10)
                self.stdout.write("%s %s %s %s (%d) %s" % (frame.midpoint, ra_string, dec_string, frame.sitecode, len(sources), frame.filename))
                
