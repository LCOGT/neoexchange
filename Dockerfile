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
# Starting from the checked-out neoexchange directory (containing this Dockerfile), build with
# docker build -t docker.lcogt.net/neoexchange:latest .
#
# Push to docker registry with
# docker push docker.lcogt.net/neoexchange:latest
#
#### To deploy
### Use the docker-compose.yml from  github.com/LCOGT/docker/compose/neoexchange/
### On docknode06.lco.gtn
### Change to the right place
# cd /mnt/docker/compose-configurations/neox/
### Pull in latest container
# docker pull docker.lcogt.net/neoexchange:latest
### Stop and remove the running container
# docker stop neox_web_1
# docker rm neox_web_1
### Start the new container
# docker-compose up -d
#
################################################################################
FROM centos:centos7
MAINTAINER LCOGT <webmaster@lcogt.net>

# nginx runs on port 80, uwsgi is linked in the nginx conf
EXPOSE 80

# The entry point is our init script, which runs startup tasks, then
# execs the supervisord daemon
ENTRYPOINT [ "/init" ]

# Setup the Python Django environment
ENV PYTHONPATH /var/www/apps
ENV DJANGO_SETTINGS_MODULE neox.settings

# Set the PREFIX env variable
ENV PREFIX /neoexchange

# Install packages and update base system
RUN yum -y install epel-release \
        && yum -y install cronie libjpeg-devel nginx python-pip mysql-devel python-devel \
        && yum -y install supervisor libssl libffi libffi-devel \
        && yum -y groupinstall "Development Tools" \
        && yum -y update \
        && yum clean all

# Setup our python env now so it can be cached
COPY neoexchange/requirements.txt /var/www/apps/neoexchange/requirements.txt

# Install the LCOGT NEO exchange Python required packages
# Then the LCOGT packages which have to be installed after the normal pip install
RUN pip install uwsgi==2.0.8 \
		&& pip install --trusted-host buildsba.lco.gtn -r /var/www/apps/neoexchange/requirements.txt \
		&& pip install pyslalib --trusted-host buildsba.lco.gtn --extra-index-url=http://buildsba.lco.gtn/python/ \
		&& pip install rise_set --trusted-host buildsba.lco.gtn --extra-index-url=http://buildsba.lco.gtn/python/

# Ensure crond will run on all host operating systems
RUN sed -i -e 's/\(session\s*required\s*pam_loginuid.so\)/#\1/' /etc/pam.d/crond

# Copy configuration files
COPY config/uwsgi.ini /etc/uwsgi.ini
COPY config/nginx/* /etc/nginx/
COPY config/processes.ini /etc/supervisord.d/processes.ini
COPY config/crontab.root /var/spool/cron/root

# Copy configuration files
COPY config/init /init

# Copy the LCOGT NEOexchange webapp files
COPY neoexchange /var/www/apps/neoexchange
