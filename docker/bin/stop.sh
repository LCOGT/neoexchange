#!/bin/bash
docker stop observations_uwsgi 2>&1 > /dev/null
docker rm observations_uwsgi 2>&1 > /dev/null
docker stop observations_nginx 2>&1 > /dev/null
docker rm observations_nginx 2>&1 > /dev/null