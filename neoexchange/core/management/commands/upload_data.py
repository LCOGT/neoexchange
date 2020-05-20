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

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage

from core.utils import search


class Command(BaseCommand):

    help = 'Upload file to S3'

    def add_arguments(self, parser):
        parser.add_argument('file', type=str, help='File to upload')
        parser.add_argument('--datadir', action="store", default=None, help="data directory for file upload")

    def handle(self, *args, **options):
        filepath = options['file']
        self.stdout.write("==== Uploading {} to S3".format(filepath))

        filename = os.path.basename(filepath)
        with open(filepath, "rb") as file:
            default_storage.save(os.path.join(options['datadir'], filename), file)
