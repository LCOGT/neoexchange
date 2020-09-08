"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2016-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

import os
from sys import argv
from datetime import datetime, timedelta
from tempfile import mkdtemp, gettempdir
import shutil
from glob import glob

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage

from core.models import DownloadProcessPipeline


class Command(BaseCommand):

    help = 'Download data from the LCO Archive'

    def add_arguments(self, parser):
        if not settings.USE_S3:
            out_path = settings.DATA_ROOT
        else:
            out_path = mkdtemp()
        parser.add_argument('--date', action="store", default=None, help='Date of the data to download (YYYYMMDD)')
        parser.add_argument('--proposal', action="store", default=None, help="Proposal code to query for data (e.g. LCO2019B-023; default is for all active proposals)")
        parser.add_argument('--datadir', default=out_path, help='Place to save data (e.g. %s)' % out_path)
        parser.add_argument('--spectraonly', default=False, action='store_true', help='Whether to only download spectra')
        parser.add_argument('--dlengimaging', default=False, action='store_true', help='Whether to download imaging for LCOEngineering')
        parser.add_argument('--numdays', action="store", default=0.0, type=float, help='How many extra days to look for')

    def handle(self, *args, **options):
        usage = "Incorrect usage. Usage: %s [YYYYMMDD] [proposal code]" % ( argv[1] )

        if isinstance(options['date'], str):
            try:
                obs_date = datetime.strptime(options['date'], '%Y%m%d')
                obs_date += timedelta(seconds=17*3600)
            except ValueError:
                raise CommandError(usage)
        else:
            obs_date = options['date']

        pipe = DownloadProcessPipeline()
        pipe.download(date=obs_date,proposals=options['proposal'])
