"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2020-2020 LCO

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
from glob import glob

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage

from core.utils import search


class Command(BaseCommand):

    help = 'Upload file to S3'

    def add_arguments(self, parser):
        parser.add_argument('path', type=str, help='local path/File to upload')
        parser.add_argument('--destdir', action="store", default=None, help="data directory for file upload")
        parser.add_argument('--ext', default=None, type=str, help='comma separated file extensions to upload. '
                                                                  'If provided will upload path/*ext (Use * for all)')
        parser.add_argument('--list', default=False, action='store_true', help='Set this flag to designate path input '
                                                                               'as pointing to a file containing a list '
                                                                               'of files,destinations to be uploaded')
        parser.add_argument('--overwrite', default=False, action='store_true', help='Set flag to overwrite data on S3')

    def handle(self, *args, **options):
        filepath = options['path']
        ext = options['ext']
        file_list = []
        search_list = []
        dest_list = []
        if not settings.USE_S3:
            self.stdout.write("WARNING: No Access to S3. Update enviornment.")
            return

        if options['list']:
            if '*' in filepath:
                list_list = glob(filepath)
            else:
                list_list = [filepath]
            for listfile in list_list:
                with open(listfile, 'r') as input_list:
                    for line in input_list:
                        if line[0] != '#':
                            search_list.append(line.rstrip())

        if ext:
            if ',' in ext:
                ext_list = ext.split(',')
            else:
                ext_list = [ext]
            if filepath[-1] != '/':
                filepath += '/'
            for ex in ext_list:
                if not search_list:
                    if ex[0] != '*':
                        ex = '*{}'.format(ex)
                    search_path = filepath + ex
                    file_list += glob(search_path)
                    dest_list.append(options['destdir'])
                else:
                    for f in search_list:
                        if ex in f or ex == '*':
                            if ',' in f and options['destdir'] is None:
                                f_split = f.split(',')
                                file_list.append(f_split[0])
                                dest_list.append(f_split[1])
                            else:
                                file_list.append(f)
                                dest_list.append(options['destdir'])
        elif search_list:
            for f in search_list:
                if ',' in f and options['destdir'] is None:
                    f_split = f.split(',')
                    file_list.append(f_split[0])
                    dest_list.append(f_split[1])
                else:
                    file_list.append(f)
                    dest_list.append(options['destdir'])
        else:
            file_list.append(filepath)
            dest_list.append(options['destdir'])

        for i, file in enumerate(file_list):
            if len(dest_list) == len(file_list):
                dest = dest_list[i]
            else:
                dest = dest_list[0]

            filename = os.path.basename(file)
            if not search(dest, filename, latest=True) or options['overwrite']:
                self.stdout.write("==== Uploading {} to S3:{}".format(file, dest))
                with open(file, "rb") as f:
                    default_storage.save(os.path.join(dest, filename), f)
            else:
                self.stdout.write("==== {} already exists on S3".format(os.path.join(dest, filename)))
        self.stdout.write("==== Uploading to S3 complete")
