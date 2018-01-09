from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from sys import argv
from astrometrics.sources_subs import fetch_list_targets, random_delay
from core.views import update_MPC_orbit


class Command(BaseCommand):
    help = 'Fetch targets text file or command line list'

    def add_arguments(self, parser):
        parser.add_argument('list_targets', nargs='+', help='Filenames and/or List of Targets to Ingest')
        parser.add_argument('--origin', help='Origin code for Target list: "M": Minor Planet Center, "N":NASA, "S":Spaceguard, "D":NEODSYS, "G":Goldstone, "A":Arecibo, "R":Goldstone & Arecibo, "L":LCOGT, "Y":Yarkovsky, "T":Trojan')

    def handle(self, *args, **options):
        usage = 'Incorrect usage. Usage must include: --origin ["M": Minor Planet Center, "N":NASA, "S":Spaceguard, "D":NEODSYS, "G":Goldstone, "A":Arecibo, "R":Goldstone & Arecibo, "L":LCOGT, "Y":Yarkovsky, "T":Trojan]'
        if options['origin'] not in ["M","N","S","D","G","A","R","L","Y","T"]:
            raise CommandError(usage)
        self.stdout.write("==== Fetching New Targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        list_targets = fetch_list_targets(options['list_targets'])
        for obj_id in list_targets:
            self.stdout.write("Reading New Target %s" % obj_id)
            update_MPC_orbit(obj_id, origin=options['origin'])
            # Wait between 10 and 20 seconds
            delay = random_delay(10, 20)
            self.stdout.write("Slept for %d seconds" % delay)
