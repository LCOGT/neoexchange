#!/bin/bash
touch /var/log/nginx/error.log
touch /var/log/nginx/access.log
mkdir -p /run
tail --pid $$ -f /var/log/nginx/access.log &
tail --pid $$ -f /var/log/nginx/error.log &
cat /var/www/apps/neoexchange/docker/config/nginx.conf | envsubst '$PREFIX $NEOEXCHANGE_UWSGI_PORT_8001_TCP_ADDR' > /etc/nginx/nginx.conf
/usr/sbin/nginx -c /etc/nginx/nginx.conf
