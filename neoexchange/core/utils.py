"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2019-2019 LCO
utils.py -- General utilities for file management in Neoexchange
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

import re
import os
from django.core.files.storage import default_storage


def search(base_dir, matchpattern, latest=False):
    try:
        _, files = default_storage.listdir(base_dir)
    except FileNotFoundError:
        return False
    if files:
        regex = re.compile(matchpattern)
        matchfiles = filter(regex.search, files)
        # Find most recent file
        if not latest:
            return matchfiles
        times = [(default_storage.get_modified_time(name=os.path.join(base_dir, i)), os.path.join(base_dir, i)) for i in matchfiles]
        if times:
            _, latestfile = max(times)
        else:
            latestfile = ''
        return latestfile
    return ''


def save_to_default(filename, out_path):
    filename_up = filename.replace(out_path, "")[1:]
    file = default_storage.open(filename_up, 'wb+')
    with open(filename, 'rb+') as f:
        file.write(f.read())
    file.close()
    return
