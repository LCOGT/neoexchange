#!/bin/bash
# usage: run_tests_warn.sh <worktree> <python> <logfile> [apps...]  -- no network, all deprecation warnings shown
WT=$1; PY=$2; LOG=$3; shift 3
cd $WT/neoexchange || exit 1
echo "=== $(date) START $PY ($($PY --version 2>&1)) net=none warnings=always ===" > $LOG
$PY -c "import django, numpy, astropy, matplotlib; print('django', django.__version__, 'numpy', numpy.__version__, 'astropy', astropy.__version__, 'mpl', matplotlib.__version__)" >> $LOG 2>&1
( time unshare -rn env PYTHONWARNINGS=always MPLBACKEND=Agg timeout 3600 $PY -W always manage.py test "$@" --noinput -v 2 ) >> $LOG 2>&1
echo "=== $(date) END exit=$? ===" >> $LOG
