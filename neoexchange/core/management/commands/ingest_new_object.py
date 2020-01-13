"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2015-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""
from sys import argv
import os
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from core.models import Body
from core.views import ingest_new_object, clean_NEOCP_object, save_and_make_revision
from astrometrics.sources_subs import packed_to_normal, parse_mpcobs, read_mpcorbit_file
import logging


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Ingest new objects from a local NEOCP 1-line file produced by e.g. find_orb'

    def add_arguments(self, parser):
        parser.add_argument('rockfile', nargs='+', type=str)

    def handle(self, *args, **options):
        for new_rock in options['rockfile']:

            body, created, msg = ingest_new_object(os.path.expanduser(new_rock))

            self.stdout.write(msg)
