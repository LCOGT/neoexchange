# -*- coding: utf-8 -*-
# Django settings for neox project.

import os, sys
from django.utils.crypto import get_random_string

VERSION = '1.7.1'

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
PRODUCTION = True if CURRENT_PATH.startswith('/var/www') else False
DEBUG = False
BRANCH = os.environ.get('BRANCH',None)
if BRANCH:
    BRANCH = '-' + BRANCH
else:
    BRANCH = ''

PREFIX = os.environ.get('PREFIX', '')

if PREFIX != '':
    FORCE_SCRIPT_NAME = '/neoexchange'

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SESSION_COOKIE_NAME='neox.sessionid'

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

ADMIN_TITLE = 'NEO exchange admin'
SUIT_CONFIG = {
    'ADMIN_NAME': 'NEO exchange admin'
}

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
STATICFILES_DIRS = [os.path.join(BASE_DIR,'core'),]

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder"
 )

MIDDLEWARE_CLASSES = (
    'opbeat.contrib.django.middleware.OpbeatAPMMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

AUTHENTICATION_BACKENDS = (
    'neox.auth_backend.LCOAuthBackend',
    'django.contrib.auth.backends.ModelBackend',
    )

ROOT_URLCONF = 'neox.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'neox.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'neox.neox_context.neox_context_processor',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LOGIN_URL = PREFIX +'/accounts/login/'

LOGIN_REDIRECT_URL = PREFIX + '/'

# GRAPPELLI_INDEX_DASHBOARD = 'neox.dashboard.CustomIndexDashboard'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.messages',
    'reversion',
    'core.apps.CoreConfig',
    'analyser.apps.AstrometerConfig',
    'opbeat.contrib.django',
)

OPBEAT = {
    'ORGANIZATION_ID': os.environ.get('NEOX_OPBEAT_ORGID',''),
    'APP_ID': os.environ.get('NEOX_OPBEAT_APPID',''),
    'SECRET_TOKEN': os.environ.get('NEOX_OPBEAT_TOKEN',''),
    'DEBUG': False,
}

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
            'formatter': 'verbose',
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
        'core' : {
            'handlers' : ['file','console'],
            'level'    : 'INFO',
        },
        'astrometrics' : {
            'handlers' : ['file','console'],
            'level'    : 'ERROR',
        },
        'photometrics' : {
            'handlers' : ['file','console'],
            'level'    : 'ERROR',
        },
        'neox': {
            'handlers':['file','console'],
            'level' : 'ERROR'
        }
    }
}

chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
SECRET_KEY = get_random_string(50, chars)

DATABASES = {
    "default": {
        # Live DB
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get('NEOX_DB_NAME', 'neoexchange'),
        "USER": os.environ.get('NEOX_DB_USER',''),
        "PASSWORD": os.environ.get('NEOX_DB_PASSWD',''),
        "HOST": os.environ.get('NEOX_DB_HOST',''),
        "CONN_MAX_AGE" : 1800,
        "OPTIONS"   : {'init_command': 'SET storage_engine=INNODB'},

    }
}

##################
# Email settings #
##################

EMAIL_USE_TLS       = True
EMAIL_HOST          = 'smtp.gmail.com'
EMAIL_PORT          =  587
DEFAULT_FROM_EMAIL  = 'NEO Exchange <neox@lco.global>'
EMAIL_HOST_USER = os.environ.get('NEOX_EMAIL_USERNAME', '')
EMAIL_HOST_PASSWORD = os.environ.get('NEOX_EMAIL_PASSWORD', '')


####################
# LCO Api settings #
####################

NEO_ODIN_USER = os.environ.get('NEOX_ODIN_USER', '')
NEO_ODIN_PASSWD = os.environ.get('NEOX_ODIN_PASSWD', '')

REQUEST_API_URL = 'https://lco.global/observe/api/user_requests/%s/requests/'
FRAMES_API_URL = 'https://lco.global/observe/api/requests/%s/frames/'
REQUEST_AUTH_API_URL = 'https://lco.global/observe/api/api-token-auth/'

ARCHIVE_FRAMES_URL = 'https://archive-api.lco.global/frames/'
REDUCED_DATA_SUFFIX = 'e90'

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
    OPBEAT['APP_ID'] = None


###################
# OAuth provider  #
###################

CLIENT_ID = os.environ.get('NEOX_RBAUTH_ID','')
CLIENT_SECRET = os.environ.get('NEOX_RBAUTH_SECRET','')
RBAUTH_TOKEN_URL = 'https://lco.global/observe/o/token/'
RBAUTH_PROFILE_API = 'https://lco.global/observe/api/profile/'
RBAUTH_PROPOSAL_API = 'https://lco.global/observe/api/proposals/'
ARCHIVE_API_URL = 'https://archive-api.lco.global'
ARCHIVE_TOKEN_URL = 'https://archive-api.lco.global/api-token-auth/'

##################
# LOCAL SETTINGS #
##################

# Allow any settings to be defined in local_settings.py which should be
# ignored in your version control system allowing for settings to be
# defined per machine.
if not CURRENT_PATH.startswith('/var/www'):
    try:
        from local_settings import *
    except ImportError as e:
        if "local_settings" not in str(e):
            raise e
