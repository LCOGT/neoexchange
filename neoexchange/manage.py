#!/usr/bin/env python3
import os
import sys
import platform

import django
from django.conf import settings

def banner():

    # The raw banner split into lines.
    lines = ("""
.__   __.  _______   ______   ___   ___
|  \ |  | |   ____| /  __  \  \  \ /  /
|   \|  | |  |__   |  |  |  |  \  V  /
|  . `  | |   __|  |  |  |  |   >   <
|  |\   | |  |____ |  `--'  |  /  .  \\
|__| \__| |_______| \______/  /__/ \__\\


* Django %(django_version)s
* Python %(python_version)s
* %(os_name)s %(os_version)s
* NEOx %(neox_version)s

""" % {
        "django_version": django.get_version(),
        "python_version": sys.version.split(" ", 1)[0],
        "os_name": platform.system(),
        "os_version": platform.release(),
        "neox_version" : settings.VERSION,
    }).splitlines()

    return "\n".join(lines)

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "neox.settings")

    from django.core.management import execute_from_command_line
    if 'runserver' in sys.argv:
        sys.stdout.write(banner())
    execute_from_command_line(sys.argv)
