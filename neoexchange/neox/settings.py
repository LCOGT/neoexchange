# -*- coding: utf-8 -*-
# Django settings for neox project.

import os, ast
import sys
from django.utils.crypto import get_random_string
import rollbar


VERSION = '3.14.1a'


CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
PRODUCTION = True if CURRENT_PATH.startswith('/var/www') else False
DEBUG = False
BRANCH = os.environ.get('BRANCH', None)
if BRANCH:
    BRANCH = '-' + BRANCH
else:
    BRANCH = ''

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SESSION_COOKIE_NAME = 'neox.sessionid'

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

# This determines if you use the Amazon S3 bucket or a local directory.
USE_S3 = ast.literal_eval(os.environ.get('USE_S3', 'False'))

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = '/var/www/html/media/'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

STATIC_ROOT = '/var/www/html/static/'
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'core'), ]

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder"
 )

MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'rollbar.contrib.django.middleware.RollbarNotifierMiddleware',
)

AUTHENTICATION_BACKENDS = (
    'neox.auth_backend.ValhallaBackend',
    'django.contrib.auth.backends.ModelBackend'
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

LOGIN_URL = '/accounts/login/'

LOGIN_REDIRECT_URL = '/'

# GRAPPELLI_INDEX_DASHBOARD = 'neox.dashboard.CustomIndexDashboard'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.messages',
    'django_dramatiq',
    'reversion',
    'rest_framework',
    'core.apps.CoreConfig',
    'analyser.apps.AstrometerConfig',
    'pipelines.apps.PipelinesConfig'
)

PIPELINES = {
    'dldata' : 'pipelines.downloaddata.DownloadProcessPipeline',
    'ephem'  : 'pipelines.ephemeris.LongTermEphemeris',
    'proc-extract'   : 'pipelines.processdata.SExtractorProcessPipeline',
    'proc-astromfit' : 'pipelines.processdata.ScampProcessPipeline',
    'proc-zeropoint' : 'pipelines.processdata.ZeropointProcessPipeline',
}

REDIS_HOSTNAME = os.environ.get('REDIS_HOSTNAME','localhost')

# Example Dramatiq configuration using Redis
DRAMATIQ_BROKER = {
    'BROKER': 'dramatiq.brokers.redis.RedisBroker',
    'OPTIONS': {
        'url': f'redis://{REDIS_HOSTNAME}:6379',
    },
    'MIDDLEWARE': [
        'dramatiq.middleware.AgeLimit',
        'dramatiq.middleware.TimeLimit',
        'dramatiq.middleware.Callbacks',
        'dramatiq.middleware.Pipelines',
        'dramatiq.middleware.Retries',
        'django_dramatiq.middleware.DbConnectionsMiddleware',
        'django_dramatiq.middleware.AdminMiddleware',
    ]
}

DRAMATIQ_RESULT_BACKEND = {
    'BACKEND': 'dramatiq.results.backends.redis.RedisBackend',
    'BACKEND_OPTIONS': {
        'url': f'redis://{REDIS_HOSTNAME}:6379',
    },
    'MIDDLEWARE_OPTIONS': {
        'result_ttl': 60000
    }
}

rollbar_default_env = 'development' if DEBUG else 'production'
ROLLBAR = {
    'access_token': os.environ.get('ROLLBAR_TOKEN',''),
    'environment' : os.environ.get('ROLLBAR_ENVIRONMENT', rollbar_default_env),
    'root': BASE_DIR,
}
rollbar.init(**ROLLBAR)

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
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        }
    },
    'loggers': {
        'django.request': {
            'handlers':['console'],
            'propagate': True,
            'level':'ERROR',
        },
        'core' : {
            'handlers' : ['console'],
            'level'    : 'INFO',
        },
        'astrometrics' : {
            'handlers' : ['console'],
            'level'    : 'ERROR',
        },
        'photometrics' : {
            'handlers' : ['console'],
            'level'    : 'ERROR',
        },
        'neox': {
            'handlers': ['console'],
            'level' : 'ERROR'
        },
        'pipelines': {
            'handlers': ['console'],
            'level' : 'INFO'
        }
    }
}

chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
SECRET_KEY = os.environ.get('SECRET_KEY', get_random_string(50, chars))

DATABASES = {
    "default": {
        # Live DB
        "ENGINE": os.environ.get('NEOX_DB_ENGINE', 'django.db.backends.mysql'),
        "NAME": os.environ.get('NEOX_DB_NAME', 'neoexchange'),
        "USER": os.environ.get('NEOX_DB_USER',''),
        "PASSWORD": os.environ.get('NEOX_DB_PASSWD',''),
        "HOST": os.environ.get('NEOX_DB_HOST',''),
    }
}

# Set MySQL-specific options
if DATABASES['default']['ENGINE'] =='django.db.backends.mysql':
    DATABASES['default']['OPTIONS'] =  { 'init_command': "SET sql_mode='STRICT_TRANS_TABLES'" }

##################
# Email settings #
##################

EMAIL_USE_TLS       = True
EMAIL_HOST          = 'smtp.gmail.com'
EMAIL_PORT          = 587
DEFAULT_FROM_EMAIL  = 'NEO Exchange <neox@lco.global>'
EMAIL_HOST_USER = os.environ.get('NEOX_EMAIL_USERNAME', '')
EMAIL_HOST_PASSWORD = os.environ.get('NEOX_EMAIL_PASSWORD', '')
EMAIL_MPC_RECIPIENTS = ['tlister@lco.global', 'jchatelain@lco.global']

####################
# LCO Api settings #
####################

THUMBNAIL_URL = 'https://thumbnails.lco.global/'

ARCHIVE_API_URL = 'https://archive-api.lco.global/'
ARCHIVE_FRAMES_URL = ARCHIVE_API_URL + 'frames/'
ARCHIVE_TOKEN_URL = ARCHIVE_API_URL + 'api-token-auth/'
ARCHIVE_TOKEN = os.environ.get('ARCHIVE_TOKEN', '')

PORTAL_API_URL = 'https://observe.lco.global/api/'
PORTAL_REQUEST_API = PORTAL_API_URL + 'requestgroups/'
PORTAL_USERREQUEST_URL = 'https://observe.lco.global/requestgroups/'
PORTAL_REQUEST_URL = 'https://observe.lco.global/requests/'
PORTAL_TOKEN_URL = PORTAL_API_URL + 'api-token-auth/'
PORTAL_TOKEN = os.environ.get('VALHALLA_TOKEN', '')
PORTAL_PROFILE_URL = PORTAL_API_URL + 'profile/'
PORTAL_INSTRUMENTS_URL = PORTAL_API_URL + 'instruments/'

ZOONIVERSE_USER = os.environ.get('ZOONIVERSE_USER', '')
ZOONIVERSE_PASSWD = os.environ.get('ZOONIVERSE_PASSWD', '')

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
        'NAME': 'test.db', # Add the name of your SQLite3 database file here.
        },
    }
    USE_S3 = False

USE_FIREFOXDRIVER = True

##############################
# Use AWS S3 for Media Files #
##############################

if USE_S3:
    # aws settings
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.getenv('AWS_DEFAULT_REGION', 'us-west-2')
    AWS_DEFAULT_ACL = None
    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    # s3 public media settings
    PUBLIC_MEDIA_LOCATION = 'data'
    MEDIA_URL = f'https://s3-{AWS_S3_REGION_NAME}.amazonaws.com/{AWS_STORAGE_BUCKET_NAME}/{PUBLIC_MEDIA_LOCATION}/'
    DEFAULT_FILE_STORAGE = 'neox.storage_backends.PublicMediaStorage'
    DATA_ROOT = os.getenv('DATA_ROOT', '')  # Set env variable on Apophis to '/apophis/eng/rocks/'
else:
    # For local use
    MEDIA_ROOT = os.getenv('MEDIA_ROOT', '/apophis/eng/media/')
    DATA_ROOT = os.getenv('DATA_ROOT', '/apophis/eng/rocks/')

##################
# LOCAL SETTINGS #
##################

# Allow any settings to be defined in local_settings.py which should be
# ignored in your version control system allowing for settings to be
# defined per machine.
if not CURRENT_PATH.startswith('/app'):
    try:
        from .local_settings import *
    except ImportError as e:
        if "local_settings" not in str(e):
            raise e
