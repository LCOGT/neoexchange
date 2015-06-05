# -*- coding: utf-8 -*-
# Django settings for neox project.

import os, sys

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
PRODUCTION = True if CURRENT_PATH.startswith('/var/www') else False
DEBUG = True
BRANCH = os.environ.get('BRANCH',None)
if BRANCH:
    BRANCH = '-' + BRANCH
else:
    BRANCH = ''

PREFIX =""
BASE_DIR = os.path.dirname(CURRENT_PATH)

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

GRAPPELLI_ADMIN_TITLE = 'NEO exchange admin'

MANAGERS = ADMINS

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.4/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ['*']

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'UTC'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = False

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = '/var/www/html/media/'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

STATIC_ROOT = '/var/www/html/static/'
STATIC_URL = PREFIX + '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR,'ingest'),]

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder"
 )

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'neox.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'neox.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# GRAPPELLI_INDEX_DASHBOARD = 'neox.dashboard.CustomIndexDashboard'

INSTALLED_APPS = (
    'grappelli',
    'neox',
    'ingest',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.messages',
    'reversion',
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format' : "[%(asctime)s] %(levelname)s %(message)s",
            'datefmt' : "%d/%b/%Y %H:%M:%S"
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'neox.log',
            'formatter': 'verbose',
            'filters': ['require_debug_false']
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'django': {
            'handlers':['file'],
            'propagate': True,
            'level':'ERROR',
        },
        'ingest' : {
            'handlers' : ['file','console'],
            'level'    : 'DEBUG',
        }
    }
}

SECRET_KEY = os.environ['SECRET_KEY']

DATABASES = {
    "default": {
        # Live DB
        "ENGINE": "django.db.backends.mysql",
        "NAME": "neoexchange",
        "USER": os.environ['NEOX_DB_USER'],
        "PASSWORD": os.environ['NEOX_DB_PASSWD'],
        "HOST": os.environ['NEOX_DB_HOST'],
        "OPTIONS"   : {'init_command': 'SET storage_engine=INNODB'},

    }
}

#######################
# Test Database setup #
#######################

if 'test' in sys.argv:
    # If you also want to speed up password hashing in test cases.
    PASSWORD_HASHERS = (
        'django.contrib.auth.hashers.MD5PasswordHasher',
    )
    # Use SQLite3 for the database engine during testing.
    DATABASES = { 'default':
        {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'test_db', # Add the name of your SQLite3 database file here.
        },
        'rbauth':
                {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'test_rbauth', # Add the name of your SQLite3 database file here.
        }
    }

##################
# LOCAL SETTINGS #
##################

# Allow any settings to be defined in local_settings.py which should be
# ignored in your version control system allowing for settings to be
# defined per machine.
# try:
#     from local_settings import *
# except ImportError as e:
#     if "local_settings" not in str(e):
#         raise e


