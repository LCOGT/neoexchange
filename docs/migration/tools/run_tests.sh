#!/bin/bash
# usage: run_tests.sh <worktree_dir> <python> <logfile> [apps...]
WT=$1; PY=$2; LOG=$3; shift 3
cd $WT/neoexchange || exit 1
echo "=== $(date) START python=$PY ($($PY --version 2>&1)) in $WT ===" > $LOG
$PY -c "import django, numpy, astropy; print('django', django.__version__, 'numpy', numpy.__version__, 'astropy', astropy.__version__)" >> $LOG 2>&1
( time timeout 5400 $PY manage.py test "$@" --noinput -v 2 ) >> $LOG 2>&1
echo "=== $(date) END exit=$? ===" >> $LOG
