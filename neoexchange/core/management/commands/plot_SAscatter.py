from django.core.management.base import BaseCommand, CommandError
from photometrics.SA_scatter import *

class Command(BaseCommand):
    def handle(self, *args, **options):
        lines = readFile(os.path.join(os.getcwd(),'photometrics/data/Solar_Standards'))
        coords = readSources()
        galcoords = genGalPlane()
        plotScatter(coords,galcoords)

