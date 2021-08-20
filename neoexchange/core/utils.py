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
from pathlib import Path
from datetime import datetime

from django.core.files.storage import default_storage
from django.core.files.base import File, ContentFile
from django.forms.models import model_to_dict

from core.models.dataproducts import DataProduct


def search(base_dir, matchpattern, latest=False):
    """
    :param base_dir: directory to search
    :param matchpattern: filename pattern to search for
    :param latest: flag to return only a single, most recently modified search result
    :return:
        If base directory doesn't exist: False
        If base directory exists, but is empty: Empty list
        If base directory exists with files and latest==False: list of matched files
        If base directory exists, latest == True, and files found: String containing filename
        If base directory exists, latest == True, and files not found: Empty string
    """
    try:
        _, files = default_storage.listdir(base_dir)
    except FileNotFoundError:
        return False
    if files:
        regex = re.compile(matchpattern)
        file_filter = filter(regex.search, files)
        matchfiles = [f for f in file_filter]
        # Find most recent file
        if not latest:
            return matchfiles
        times = [(default_storage.get_modified_time(name=os.path.join(base_dir, i)), os.path.join(base_dir, i)) for i in matchfiles]
        if times:
            _, latestfile = max(times)
        else:
            latestfile = ''
        return latestfile
    return []


def save_to_default(filename, out_path):
    filename_up = filename.replace(out_path, "")[1:]
    file = default_storage.open(filename_up, 'wb+')
    with open(filename, 'rb+') as f:
        file.write(f.read())
    file.close()
    return


def save_dataproduct(obj, filepath, filetype, filename=None, content=None, force=False):
    if not filename:
        filename = Path(filepath).name
    try:
        dp = DataProduct.objects.get(filetype=filetype, product__endswith=filename)
    except DataProduct.DoesNotExist:
        dp = DataProduct()
    if dp.update is False and force is False:
        return
    dp.content_object = obj
    dp.filetype = filetype
    if force is True:
        dp.update = False
    if filetype in [DataProduct.CSV, DataProduct.PDS_XML, DataProduct.ALCDEF_TXT]:
        mode = 'r'
    else:
        mode = 'rb'
    if not content and not filepath:
        return
    if content:
        file_obj = ContentFile(content)
        file_obj.name = filename
        dp.product = file_obj
        dp.created = datetime.utcnow()
        dp.save()
        return
    with open(filepath, mode) as f:
        file_obj = File(f)
        file_obj.name = filename
        dp.product = file_obj
        dp.created = datetime.utcnow()
        dp.save()
    return
