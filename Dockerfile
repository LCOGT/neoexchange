################################################################################
#
# Runs the LCO Python Django NEO Exchange webapp using nginx + gunicorn
#
# The change from uwsgi to gunicorn was made to support python 3.6. Since usgi is 
# linked against the python libraries, it is hard to support the non-system python
# we want to use.
# The decision to run both nginx and gunicorn in the same container was made because
# it avoids duplicating all of the Python code and static files in two containers.
# It is convenient to have the whole webapp logically grouped into the same container.
#
# You can choose to expose the nginx and gunicorn ports separately, or you can
# just default to using the nginx port only (recommended). There is no
# requirement to map all exposed container ports onto host ports.
#

################################################################################
FROM centos:7
MAINTAINER LCOGT <webmaster@lco.global>

# nginx runs on port 80, gunicorn is linked in the nginx conf
EXPOSE 80

# Add path to python3.6
ENV PATH=/opt/lcogt-python36/bin:$PATH

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
        && yum -y install cronie libjpeg-devel nginx \
                supervisor libssl libffi libffi-devel \
                mariadb-devel gcc gcc-gfortran openssl-devel ImageMagick \
                less wget which tcsh plplot plplot-libs plplot-devel \
                git gcc-c++ ncurses-devel\
        && yum -y update

# Install Developer Toolset 7 for newer g++ version
RUN yum -y install centos-release-scl \
        && yum -y install devtoolset-7

# Enable LCO repo and install extra packages
COPY config/lcogt.repo /etc/yum.repos.d/lcogt.repo
RUN yum -y install lcogt-python36 sextractor cdsclient scamp mtdlink\
        && yum clean all

ENV PIP_TRUSTED_HOST buildsba.lco.gtn

# Setup our python env now so it can be cached
COPY neoexchange/requirements.txt /var/www/apps/neoexchange/requirements.txt

# Install the LCO NEO exchange Python required packages
# Upgrade pip first
# Then the LCO packages which have to be installed after the normal pip install
# numpy needs to be explicitly installed first otherwise pySLALIB
# fails with a missing numpy.distutils.core reference for...reasons...
RUN pip3 install -U numpy \
    && pip3 install -U pip \
    && pip3 install --trusted-host $PIP_TRUSTED_HOST -r /var/www/apps/neoexchange/requirements.txt \
    && rm -rf ~/.cache/pip

# Ensure crond will run on all host operating systems
RUN sed -i -e 's/\(session\s*required\s*pam_loginuid.so\)/#\1/' /etc/pam.d/crond

# Copy operating system configuration files
COPY docker/ /

# Copy the LCO NEOexchange webapp files
COPY neoexchange /var/www/apps/neoexchange

# Download and build find_orb
RUN mkdir /tmp/git_find_orb \
    && cd /tmp/git_find_orb \
    && git clone https://github.com/Bill-Gray/lunar.git \
    && git clone https://github.com/Bill-Gray/sat_code.git \
    && git clone https://github.com/Bill-Gray/jpl_eph.git \
    && git clone https://github.com/Bill-Gray/find_orb.git

# Start a new shell and enable the Developer Toolset 7 toolchain so we get newer (7.3) g++
SHELL ["scl", "enable devtoolset-7"]
RUN cd /tmp/git_find_orb \
    && cd lunar && make && make install && cd .. \
    && cd jpl_eph && make && make install && cd .. \
    && cd lunar && make integrat && make install && cd .. \
    && cd sat_code && make && make install && cd .. \
    && cd find_orb && make && make install && cp ps_1996.dat elp82.dat /root/.find_orb && cd .. \
    && cp /root/bin/fo /usr/local/bin/ \
    && chmod 755 /root \
    && rm -rf /tmp/git_find_orb

# Copy default findorb config file
COPY neoexchange/photometrics/configs/environ.def /root/.find_orb/
RUN chown -R nginx:nginx /root/.find_orb && chmod 2775 /root/.find_orb
