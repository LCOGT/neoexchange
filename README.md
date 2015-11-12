NEO Exchange
============

Portal for scheduling observations of NEOs using LCOGT

Local Setup
-----------

Construct a Python Virtual Environment (virtualenv) by executing:  
```bash
virtualenv <path to virtualenv>
source <path to virtualenv>/bin/activate # for bash-shells
```

or:  

`source <path to virtualenv>/bin/activate.csh # for (t)csh-shells`  

then:

`pip install -r neoexchange/requirements.txt`

You will need to create a `neox/local_settings.py` file which has details of your database setup and local filesystem e.g.

```
import os, sys

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
BASE_DIR = os.path.dirname(CURRENT_PATH)

SECRET_KEY = '<50 random characters>'

PREFIX =""
DEBUG = True
PRODUCTION = False
STATIC_ROOT =  '<filesystem path>'
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR,'core'),]

OPBEAT = {
    'ORGANIZATION_ID': '',
    'APP_ID': '',
    'SECRET_TOKEN': '',
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "neoexchange.db",
        "USER": "",
        "PASSWORD":  "",
        "HOST": "",
    }
}
```

Deployment
----------

You will need to set up 3 environment variables before deploying (if you are just locally testing see instructions below).

If you are using BASH or ZSH add the following to your .profile or .zshrc files:
```bash
export NEOX_DB_USER='<insert your DB username>'
export NEOX_DB_PASSWD='<insert your DB password>'
export NEOX_DB_HOST='<insert the name of your DB server>'
```

Docker
------
If you are building a Docker container use the following syntax:
```bash
docker build -t docker.lcogt.net/neoexchange:latest .
```
This will build a Docker image which will need to be pushed into a Docker registry with:
```bash
docker push docker.lcogt.net/neoexchange:latest
```
Starting a Docker container from this image can be done with a `docker run` command or using `docker-compose`.


Local Testing
-------------

For local testing you will probably want to create a
`neoexchange/neox/local_settings.py` file to point at a local test database and
to switch on `DEBUG` for easier testing. An example file would look like:
```python
import sys, os

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
BASE_DIR = os.path.dirname(CURRENT_PATH)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'neox.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

DEBUG = True

# Use a different database file when testing or exploring in the shell.
if 'test' in sys.argv or 'test_coverage' in sys.argv or 'shell' in sys.argv:
    DATABASES['default']['ENGINE'] = 'django.db.backends.sqlite3'
    DATABASES['default']['NAME'] = 'test.db'
    DATABASES['default']['USER'] = ''
    DATABASES['default']['PASSWORD'] = ''

STATIC_ROOT = os.path.abspath(os.path.join(BASE_DIR, '../../static/'))
```

To prepare the local SQLite DB for use, you should follow these steps:

1. `cd neoexchange\neoexchange`
2. Run `python manage.py syncdb`. This will perform migrations as necessary.
