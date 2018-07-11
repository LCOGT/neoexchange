from django.core.management.base import BaseCommand, CommandError
from photometrics.SA_scatter import *

class Command(BaseCommand):
    def handle(self, *args, **options):
        lines = readFile(os.path.join(os.getcwd(),'photometrics/data/Solar_Standards'))
        scoords = readSources('Solar')
        fcoords = readSources('Flux')
        galcoords = genGalPlane()
        ax = plt.figure().gca()
        plotScatter(ax,scoords,galcoords,'b.')
        plotScatter(ax,fcoords,galcoords,'g.')
        plt.show()
