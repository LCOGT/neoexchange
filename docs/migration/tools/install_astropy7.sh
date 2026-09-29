#!/bin/bash
set -x
SCR=${SCRATCH:-/tmp/neox-migration}; mkdir -p $SCR
V=$SCR/venv311_astropy7
rm -rf $V; /usr/bin/python3.11 -m venv $V || exit 1
$V/bin/python -m pip install -q --upgrade pip
# main's requirements with the science pins lifted: astropy 7.x, photutils 2.x, aplpy 2.2.1, matplotlib 3.8.x; numpy stays 1.26.4
sed -E 's/^astropy<6\.0$/astropy>=7,<8/; s/^photutils$/photutils>=2,<3/; s/^aplpy$/aplpy>=2.2.1/; s/^matplotlib<3\.5\.2$/matplotlib>=3.8,<3.9/; /^nose$/d' ${REPO:-$(git rev-parse --show-toplevel)}/neoexchange/requirements.txt > $SCR/req_astropy7.txt
diff ${REPO:-$(git rev-parse --show-toplevel)}/neoexchange/requirements.txt $SCR/req_astropy7.txt
$V/bin/python -m pip --no-cache-dir install numpy==1.26.4 wheel 2>&1 | tail -1
$V/bin/python -m pip --no-cache-dir install -r $SCR/req_astropy7.txt 2>&1 | tail -4
echo "RESULT_install=$?"
$V/bin/python -m pip check
$V/bin/python -m pip freeze | grep -iE '^(Django|numpy|astropy|photutils|APLpy|aplpy|matplotlib|pyslalib|astroquery|scipy|pyerfa|bokeh|Jinja2|MarkupSafe|pillow)=='
echo "=== DONE ==="
