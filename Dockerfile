################################################################################
#
# Runs the LCOGT Python Django NEO Exchange webapp using nginx + uwsgi
#
# The decision to run both nginx and uwsgi in the same container was made because
# it avoids duplicating all of the Python code and static files in two containers.
# It is convenient to have the whole webapp logically grouped into the same container.
#
# You can choose to expose the nginx and uwsgi ports separately, or you can
# just default to using the nginx port only (recommended). There is no
# requirement to map all exposed container ports onto host ports.
#
# Build with
# docker build -t docker.lcogt.net/neoexchange:latest .
#
# Push to docker registry with
# docker push docker.lcogt.net/neoexchange:latest
#
# To run with nginx + uwsgi both exposed:
# docker run -d -p 8200:80  --name=neox docker.lcogt.net/neoexchange:latest
# Or use the docker-compose.yml from  github.com/LCOGT/docker/compose/neoexchange/
#
################################################################################
FROM centos:centos7
MAINTAINER LCOGT <webmaster@lcogt.net>

# Install packages and update base system
RUN yum -y install epel-release \
        && yum -y install cronie libjpeg-devel nginx python-pip mysql-devel python-devel supervisor \
        && yum -y groupinstall "Development Tools" \
        && yum -y update

# Setup our python env now so it can be cached
COPY neoexchange/requirements.txt /var/www/apps/neoexchange/requirements.txt
<<<<<<< HEAD

# Install the LCOGT NEO exchange Python required packages
# Then the LCOGT packages which have to be installed after the normal pip install
RUN pip install pip==1.3 && pip install uwsgi==2.0.8 \
		&& pip install -r /var/www/apps/neoexchange/requirements.txt
		&& pip install pyslalib --extra-index-url=http://buildsba.lco.gtn/python/ \
=======
# Install the LCOGT NEO exchange Python required packages
RUN pip install pip==1.3 && pip install uwsgi==2.0.8 \
		&& pip install -r /var/www/apps/neoexchange/requirements.txt

# LCOGT packages which have to be installed after the normal pip install
RUN pip install pyslalib --extra-index-url=http://buildsba.lco.gtn/python/ \
>>>>>>> origin/master
		&& pip install rise_set --extra-index-url=http://buildsba.lco.gtn/python/

# Ensure crond will run on all host operating systems
RUN sed -i -e 's/\(session\s*required\s*pam_loginuid.so\)/#\1/' /etc/pam.d/crond

# Setup the Python Django environment
ENV PYTHONPATH /var/www/apps
ENV DJANGO_SETTINGS_MODULE neox.settings

# Copy configuration files
COPY config/uwsgi.ini /etc/uwsgi.ini
COPY config/nginx/* /etc/nginx/
COPY config/processes.ini /etc/supervisord.d/processes.ini
COPY config/crontab.root /var/spool/cron/root

# nginx runs on port 80, uwsgi is linked in the nginx conf
EXPOSE 80

# The entry point is our init script, which runs startup tasks, then
# execs the supervisord daemon
ENTRYPOINT [ "/init" ]

# Copy configuration files
COPY config/init /init

# Copy the LCOGT Mezzanine webapp files
COPY neoexchange /var/www/apps/neoexchange

# Setup the LCOGT NEOx webapp
RUN python /var/www/apps/neoexchange/manage.py collectstatic --noinput
