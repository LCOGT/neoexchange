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
# To run with nginx only:
# docker run -d -p 8200:8200 --name=neoexchange lcogtwebmaster/lcogt:neoexchange_$BRANCH
#
# To run with nginx + uwsgi both exposed:
# docker run -d -p 8200:8200 -p 8201:8201 --name=neox lcogtwebmaster/lcogt:neoexchange_$BRANCH
#
# See the notes in the code below about NFS mounts.
#
################################################################################
FROM centos:centos7
MAINTAINER LCOGT <webmaster@lcogt.net>

# Install packages and update base system
RUN yum -y install epel-release \
        && yum -y install cronie libjpeg-devel nginx python-pip mysql-devel python-devel supervisor \
        && yum -y groupinstall "Development Tools" \
        && yum -y update

# Ensure crond will run on all host operating systems
RUN sed -i -e 's/\(session\s*required\s*pam_loginuid.so\)/#\1/' /etc/pam.d/crond

# Setup the Python Django environment
ENV PYTHONPATH /var/www/apps
ENV DJANGO_SETTINGS_MODULE neox.settings
ENV BRANCH ${BRANCH}
#ENV BUILDDATE ${BUILDDATE}

# Copy configuration files
COPY config/uwsgi.ini /etc/uwsgi.ini
COPY config/nginx/* /etc/nginx/
COPY config/neoexchange.ini /etc/supervisord.d/neoexchange.ini
COPY config/crontab.root /var/spool/cron/root

# nginx runs on port 8200, uwsgi runs on port 8201
EXPOSE 8200 8201

# Entry point is the supervisord daemon
ENTRYPOINT [ "/usr/bin/supervisord", "-n" ]

# Copy the LCOGT Mezzanine webapp files
COPY neoexchange /var/www/apps/neoexchange

# Install the LCOGT NEO exchange Python required packages
RUN pip install pip==1.3 && pip install uwsgi==2.0.8 \
		&& pip install -r /var/www/apps/neoexchange/pip_requirements.txt \
# LCOGT packages which have to be installed after the normal pip install
		&& pip install pyslalib --extra-index-url=http://buildsba.lco.gtn/python/ \
		&& pip install rise_set --extra-index-url=http://buildsba.lco.gtn/python/

# Setup the LCOGT Mezzanine webapp
RUN python /var/www/apps/neoexchange/manage.py validate
RUN python /var/www/apps/neoexchange/manage.py collectstatic --noinput
RUN python /var/www/apps/neoexchange/manage.py syncdb --noinput
RUN python /var/www/apps/neoexchange/manage.py migrate --noinput
