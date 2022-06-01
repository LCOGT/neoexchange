# Local Setup

## Install 
Construct a Python Virtual Environment (virtualenv) by executing:  
```bash
python3 -m venv <path to virtualenv>
source <path to virtualenv>/bin/activate # for bash-shells
```

or:  

`source <path to virtualenv>/bin/activate.csh # for (t)csh-shells`  

then:

`pip3 install -r neoexchange/requirements.txt`

You will need to create a `neox/local_settings.py` file which has details of your database setup and local filesystem e.g.

```
import os, sys
import rollbar

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
BASE_DIR = os.path.dirname(CURRENT_PATH)

SECRET_KEY = '<50 random characters>'

DEBUG = True
PRODUCTION = False
STATIC_ROOT =  '<filesystem path>'
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR,'core'),]

ROLLBAR = {
    'access_token': os.environ.get('ROLLBAR_TOKEN',''),
    'environment': 'development' if DEBUG else 'production',
    'root': BASE_DIR,
}
rollbar.init(**ROLLBAR)

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

### Install on MacOS X M1 (Big Sur)

* Install HomeBrew from https://brew.sh/
* Install Fortran compiler with `brew install gfortran`
* Install database backends: `brew install mysql postgresql`
* Get an `arm64` version of Python via Miniconda from https://github.com/conda-forge/miniforge (Direct link: https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh) and install it
* Install some hard to compile packages via `conda`: `conda install numpy scipy astropy`
* Install remainder of dependencies: `pip install -r requirements.txt`

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
docker build --pull -t docker.lco.global/neoexchange:latest .
```
This will build a Docker image which will need to be pushed into a Docker registry with:
```bash
docker push docker.lco.global/neoexchange:latest
```
Starting a Docker container from this image can be done with a `docker run` command or using `docker-compose`.

In order for the updating of orbital elements for close-passing objects to work,
there needs to be a mapping of a filesystem containing the JPL DE430 binary
ephemeris into the container. This needs to be available under `/ephemerides`.
This can be done with e.g.
`-v /mnt/docker/neoexchange/ephemerides:/ephemerides:ro`
on the Docker command line or adding this to the 'Volumes' tab in Rancher when
upgrading.

For the plotting of the flux standards, a `cdbs/ctiostan/` directory needs to be
created in the file system pointed at by `DATA_ROOT`. Inside this directory
should be placed the `f<objectname>.dat` files and the `aaareadme.ctio` file
from `ftp://ftp.eso.org/pub/stecf/standards/ctiostan/`. The other objects from
the `hststan`, `okestan` and `wdstan` directories of the FTP site should also be
included in the `cdbs/ctiostan` directory.

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

## Async testing

- You will need to update your environment with the new packages from `requirements.txt`.
- Install [redis](https://redis.io/topics/quickstart) on your local system
- Open 3 terminal windows:
- Run `redis-server` in one terminal (this is a simple DB for holding the task states)
- Run `./manage.py rundramatiq` in another (this is the message/task broker)
- Run `./manage.py runserver` as normal in the third

The `dramatiq` process does not autoreload, so if you change your code it will need to be manually stop/started

## Downloading dev data

Sometimes it is useful to have a representative snapshot of the live database. There are 2 parts: 1) on the deployed pod, export data, 2) on your local machine import data

To log in to a shell on the deployed pod:

```
kubectl exec -it <NAME OF POD> -n prod -c backend -- /bin/sh
```

When in the shell run:
```
% ./manage.py export_test_fixtures
```

On your local machine:
```
% kubectl -n prod cp <NAME OF POD>:/var/www/apps/neoexchange/core/fixtures <PATH TO NEOX>/neoexchange/core/fixtures -c backend
% ./manage.py import_test_fixtures
```

If you encounter an `error: unexpected EOF`, try copying the files individually from `/core/fixtures/`
