import os, sys
from django.conf import settings

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'o*^^im(*!@_9h9$c_nd6=)tnmm!bn^8s0v$gnlb@g(mnfe4xmq'


if not settings.CURRENT_PATH.startswith('/var/www'):
	DEBUG = True
	PRODUCTION = False
	STATIC_ROOT =  '/Users/egomez/Sites/static'
	STATIC_URL = '/static/'
	STATICFILES_DIRS = [os.path.join(settings.BASE_DIR,'ingest'),]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'neox.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}