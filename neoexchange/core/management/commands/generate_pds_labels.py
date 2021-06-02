"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2021-2021 LCO

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
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from photometrics.pds_subs import create_pds_labels


class Command(BaseCommand):
    help = 'Create PDS4 XML label files for processed FITS files'

    def add_arguments(self, parser):
        out_path = settings.DATA_ROOT
        schemadir = os.path.abspath(os.path.join('photometrics', 'configs', 'PDS_schemas'))
        parser.add_argument('datadir', action="store", default=out_path, help='Path for processed data (e.g. {:s})'.format(out_path))
        parser.add_argument('--schemadir', action="store", default=schemadir, help='Path to PDS schemas (e.g. {:s})'.format(schemadir))

    def handle(self, *args, **options):
        now = datetime.utcnow()
        now_string = now.strftime('%Y-%m-%d %H:%M')
        self.stdout.write("==== Starting Processing FITS files in {} to PDS4 labels {} ====".format(options['datadir'], now_string))

        xml_labels = create_pds_labels(options['datadir'], options['schemadir'])

        now = datetime.utcnow()
        now_string = now.strftime('%Y-%m-%d %H:%M')
        self.stdout.write("==== Completed Processing {:d} FITS files to PDS4 labels {} ====".format(len(xml_labels), now_string))
