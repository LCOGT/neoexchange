'''
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2014-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''
import os

# Astropy needs to write config and cache files into its home directory. When
# running under gunicorn as an unprivileged user, it doesn't have a home
# directory (aaah). Need to set the XDG_* environment variables to give these
# files somewhere to go.
os.environ.setdefault("XDG_CONFIG_HOME", "/var/www/apps/astropyconfig")
os.environ.setdefault("XDG_CACHE_HOME", "/var/www/apps/astropycache")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "neox.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
