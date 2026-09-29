#!/bin/bash
# Read-only inventory of the NEOexchange checkout + runtime on apophis2 (Q18 in MIGRATION_PLAN.md).
# Run from the workstation:   ssh apophis2 bash -s < docs/migration/tools/apophis2_inventory.sh > docs/migration/apophis2/inventory-$(date +%F).txt
# Nothing here writes to the repo or the host (git --no-optional-locks, no fetch/stash/checkout). Secrets are redacted before output.
red() { sed -E 's/((TOKEN|PASSWORD|PASSWD|SECRET|KEY|ACCESS)[A-Za-z_]*[[:space:]]*[=:][[:space:]]*).*/\1<redacted>/I'; }
echo "### host"; hostname; cat /etc/redhat-release 2>/dev/null; uname -r; ldd --version 2>/dev/null | head -1; openssl version 2>/dev/null; date; uptime
echo "### git"; git --version
cd ~/git/neoexchange-devel || { echo "NO REPO at ~/git/neoexchange-devel"; exit 1; }
G="git --no-optional-locks"
echo "### repo"; pwd; echo "branch: $($G rev-parse --abbrev-ref HEAD)"; echo "HEAD: $($G log -1 --format='%H %ad %an %s' --date=short)"; $G remote -v | head -2
echo "### origin/pipelines as last fetched here"; $G rev-parse origin/pipelines 2>/dev/null; $G log -1 --format='%h %ad %s' --date=short origin/pipelines 2>/dev/null; echo "last fetch: $(stat -c '%y' .git/FETCH_HEAD 2>/dev/null)"
echo "### local commits not on origin/pipelines (here)"; $G log --format='%h %ad %s' --date=short origin/pipelines..HEAD 2>/dev/null | head -40
echo "### commits on origin/pipelines (here) not in HEAD"; $G rev-list --count HEAD..origin/pipelines 2>/dev/null
echo "### stash"; $G stash list
echo "### status counts"; $G status --porcelain --untracked-files=all | cut -c1-2 | sort | uniq -c
echo "### tracked modifications (diffstat)"; $G diff --stat | tail -60
echo "### staged"; $G diff --cached --stat | tail -10
echo "### untracked files (size  path), excluding pyc/fits/fz/png/jpg/gif/db/log"; $G ls-files --others --exclude-standard | grep -vE '\.(pyc|fits|fz|png|jpg|gif|db|log)$|__pycache__|\.ipynb_checkpoints' | while read f; do printf '%10s  %s\n' "$(stat -c %s "$f" 2>/dev/null)" "$f"; done | head -400
echo "### untracked file counts by extension"; $G ls-files --others --exclude-standard | grep -oE '\.[A-Za-z0-9]+$' | sort | uniq -c | sort -rn | head -15
echo "### ignored-but-present files of interest"; $G ls-files --others --ignored --exclude-standard | grep -vE '__pycache__|\.pyc$|\.ipynb_checkpoints' | head -40
echo "### local branches"; $G branch -vv | head -40
echo "### reflog (recent)"; $G reflog -n 20 --date=short
echo "### other checkouts under ~/git"; for d in ~/git/*/; do [ -d "$d/.git" ] && echo "$d  branch=$(git -C "$d" --no-optional-locks rev-parse --abbrev-ref HEAD 2>/dev/null)  head=$(git -C "$d" --no-optional-locks log -1 --format='%h %ad' --date=short 2>/dev/null)  dirty_lines=$(git -C "$d" --no-optional-locks status --porcelain 2>/dev/null | wc -l)"; done
echo "### python / venvs"; which python python3 2>/dev/null; python --version 2>&1; python3 --version 2>&1; echo "VIRTUAL_ENV=$VIRTUAL_ENV"; grep -nE 'venv|activate|conda|PYTHONPATH' ~/.bashrc ~/.bash_profile ~/.profile 2>/dev/null | head -10
for a in $(find ~ -maxdepth 4 -path '*/bin/activate' -type f 2>/dev/null | head -8); do v=$(dirname $(dirname $a)); echo "--- venv $v: $($v/bin/python --version 2>&1) openssl=$($v/bin/python -c 'import ssl;print(ssl.OPENSSL_VERSION)' 2>&1 | head -1)"; $v/bin/python -m pip freeze 2>/dev/null | grep -iE '^(Django|numpy|astropy|photutils|pySLALIB|pyslalib|dramatiq|django-dramatiq|djangorestframework|redis|watchdog|matplotlib|scipy|bokeh|Jinja2|MarkupSafe|psycopg2-binary|calviacat|mastcasjobs|astroquery|APLpy|aplpy|selenium)==' | tr '\n' ' '; echo; done
echo "### cronwrapper files (redacted)"; ls -la ~/cronwrapper* 2>/dev/null; for f in ~/cronwrapper*; do [ -f "$f" ] && { echo "--- $f"; red < "$f"; }; done
echo "### crontab (redacted)"; crontab -l 2>/dev/null | red
echo "### ~/bin"; ls -la ~/bin 2>/dev/null | head -30
echo "### processes (redis/dramatiq/manage.py/gunicorn)"; ps -eo user,pid,etime,cmd | grep -E 'redis|dramatiq|manage\.py|gunicorn' | grep -v grep
echo "### systemd units"; systemctl list-units --type=service --all 2>/dev/null | grep -iE 'redis|dramatiq|neox|neoexchange'; systemctl list-unit-files 2>/dev/null | grep -iE 'redis|dramatiq|neox|neoexchange'; ls ~/.config/systemd/user 2>/dev/null
echo "### binaries"; for b in sex sextractor scamp swarp hotpants mtdlink fo period_scan convexinv astwarp astnoisechisel astconvertt unix2dos redis-server node docker podman; do printf '%-14s %s\n' $b "$(command -v $b 2>/dev/null || echo -)"; done
echo "### rpms of interest"; rpm -qa 2>/dev/null | grep -iE 'scamp|sextractor|swarp|hotpants|mtdlink|cdsclient|gnuastro|redis|^python3|openssl11|rh-python|devtoolset' | sort
echo "### find_orb config"; ls -la ~/.find_orb 2>/dev/null | head -8
echo "### data roots"; ls -ld /data/eng/rocks /apophis/eng/rocks 2>/dev/null; df -h /data/eng/rocks 2>/dev/null | tail -1
echo "### env var names present (values omitted)"; env | grep -oE '^(NEOX|ARCHIVE|VALHALLA|USE_S3|DATA_ROOT|MEDIA_ROOT|AWS|REDIS|ROLLBAR|SECRET)[A-Z_0-9]*' | sort
echo "### local_settings.py (redacted)"; red < neoexchange/neox/local_settings.py 2>/dev/null
echo "### END"
