'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2015-2016 LCOGT

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''
from sys import argv
import os
from glob import glob

from core.models import Body, SourceMeasurement, Frame
from core.views import create_source_measurement
import logging

from django.core.management.base import BaseCommand, CommandError
from datetime import datetime

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Ingest measurement of old objects from a local MPC 80-column.'

    def add_arguments(self, parser):
        parser.add_argument('dir_path', nargs='+', type=str)

    def handle(self, *args, **options):
        new_rocks_path = os.path.expanduser(options['dir_path'][0])
        new_rocks = glob(os.path.join(new_rocks_path, '*.dat'))

        if len(new_rocks) == 0:
            self.stdout.write("No files found in %s" % new_rocks_path)
            return
        for new_rock in new_rocks:
            try:
                obsfile_fh = open(new_rock, 'r')
                self.stdout.write("Reading %s" % os.path.basename(new_rock))
                obslines = obsfile_fh.readlines()
                obsfile_fh.close()

                measure = create_source_measurement(obslines)
                if measure:
                    msg = "\033[92mCreated SourceMeasurements for %s \033[0m" % new_rock
                else:
                    msg = "\033[93mCould not create SourceMeasurements for %s \033[0m" % new_rock
                self.stdout.write(msg)
            except IOError:
                self.stdout.write("File %s not found" % new_rock)
