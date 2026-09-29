#!/bin/bash
# Empirical test: can the *current pipelines* requirements.txt install under Python 3.11 (mimicking the Dockerfile order)?
set -x
SCR=${SCRATCH:-/tmp/neox-migration}; mkdir -p $SCR
R=${REPO:-$(git rev-parse --show-toplevel)}
V=$SCR/venv311_asis
rm -rf $V
/usr/bin/python3.11 -m venv $V || exit 1
$V/bin/python -m pip install --upgrade pip 2>&1 | tail -1
$V/bin/python -m pip --version
$V/bin/python -c "import setuptools; print('setuptools', setuptools.__version__)"
echo "=== STEP 1: numpy==1.23.5 wheel ==="
$V/bin/python -m pip --no-cache-dir install numpy==1.23.5 wheel 2>&1 | tail -3
echo "=== STEP 2: pyslalib alone (default build isolation) ==="
$V/bin/python -m pip --no-cache-dir install pyslalib 2>&1 | tail -15
echo "RESULT_pyslalib_isolated=$?"
$V/bin/python -c "from pyslalib import slalib; print('pyslalib import OK', slalib.sla_dtt(51544.5))" 2>&1
echo "=== STEP 3: full requirements.txt as-is ==="
$V/bin/python -m pip --no-cache-dir install -r $R/neoexchange/requirements.txt 2>&1 | tail -40
echo "RESULT_full=$?"
echo "=== FREEZE ==="
$V/bin/python -m pip freeze 2>/dev/null | grep -iE '^(Django|numpy|astropy|photutils|bokeh|matplotlib|pySLALIB|dramatiq|django-dramatiq|djangorestframework|Jinja2|MarkupSafe|selenium|gunicorn|gevent|redis|watchdog|psycopg2|pillow|aplpy|scipy|nose|ipython)=='
echo "=== DONE ==="
