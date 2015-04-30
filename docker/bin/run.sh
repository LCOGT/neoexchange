#!/bin/bash
BRANCH=`git name-rev --name-only HEAD`
docker stop_uwsgi 2>&1 > /dev/null
docker rm_uwsgi 2>&1 > /dev/null
docker stop_nginx 2>&1 > /dev/null
docker rm_nginx 2>&1 > /dev/null
docker login --username="lcogtwebmaster" --password="lc0GT!" --email="webmaster@lcogt.net"
if [ "$DEBUG" != "" ]; then
    DEBUGENV="-e DEBUG=True"
fi
if [ "$PREFIX" == "" ]; then
    PREFIX=""
fi
docker run -d --name_uwsgi -e PREFIX=$PREFIX $DEBUGENV lcogtwebmaster/lcogt_$BRANCH /var/www/apps/docker/bin/uwsgi.sh
docker run -d --name_nginx -p 8000:8000 -e PREFIX=$PREFIX $DEBUGENV --link_uwsgi_uwsgi lcogtwebmaster/lcogt_$BRANCH /var/www/apps/docker/bin/nginx.sh
if [ "$DEBUG" != "" ]; then
    docker logs -f_nginx &
    docker logs -f_uwsgi &
fi