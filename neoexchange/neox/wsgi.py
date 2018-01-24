'''
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2014-2018 LCO

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
# running under uwsgi and the uwsgi user, it doesn't have a home (aaah). Need
# to set environment variables to give these files somewhere to go.

try:
    envvars = {    
        'XDG_CONFIG_HOME': '/var/www/apps/astropyconfig',
        'XDG_CACHE_HOME' : '/var/www/apps/astropycache'
    }
    os.environ.update(envvars)
except:
    pass

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "neox.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)
