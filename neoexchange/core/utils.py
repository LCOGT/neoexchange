import re

from django.core.files.storage import default_storage


def search(base_dir, matchpattern, latest=False):
    try:
        _, files = default_storage.listdir(path=base_dir)
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
