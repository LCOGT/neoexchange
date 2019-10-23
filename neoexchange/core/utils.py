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
