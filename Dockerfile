FROM centos:7
MAINTAINER LCOGT <webmaster@lco.global>

# Add path to python3.6
ENV PATH=/opt/lcogt-python36/bin:$PATH

# The entry point is our init script, which runs startup tasks, then starts gunicorn
ENTRYPOINT [ "/init" ]

# Setup the Python Django environment
ENV PYTHONPATH /var/www/apps
ENV DJANGO_SETTINGS_MODULE neox.settings

# Supercronic environment variables
ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.1.9/supercronic-linux-amd64 \
    SUPERCRONIC=supercronic-linux-amd64 \
    SUPERCRONIC_SHA1SUM=5ddf8ea26b56d4a7ff6faecdd8966610d5cb9d85

# Supercronic installation
RUN curl -fsSLO "$SUPERCRONIC_URL" \
        && echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
        && chmod +x "$SUPERCRONIC" \
        && mv "$SUPERCRONIC" "/usr/local/bin/${SUPERCRONIC}" \
        && ln -s "/usr/local/bin/${SUPERCRONIC}" /usr/local/bin/supercronic

# Enable LCO RPM repository
COPY docker/etc/yum.repos.d/lcogt.repo /etc/yum.repos.d/lcogt.repo

# Install packages and update base system
RUN yum -y install centos-release-scl epel-release \
        && yum -y install \
            cdsclient \
            devtoolset-7 \
            gcc \
            gcc-c++ \
            gcc-gfortran \
            git \
            ImageMagick \
            lcogt-python36 \
            less \
            libffi-devel \
            libjpeg-devel \
            libssl \
            mariadb-devel \
            mtdlink \
            ncurses-devel \
            openssl-devel \
            plplot-devel \
            scamp \
            sextractor \
            tcsh \
            wget \
            which \
        && yum -y clean all

# Setup our python env now so it can be cached
COPY neoexchange/requirements.txt /var/www/apps/neoexchange/requirements.txt

# Install the LCO NEO exchange Python required packages
# Upgrade pip first
# Then the LCO packages which have to be installed after the normal pip install
# numpy needs to be explicitly installed first otherwise pySLALIB
# fails with a missing numpy.distutils.core reference for...reasons...
RUN pip3 --no-cache-dir install --upgrade pip \
    && pip3 --no-cache-dir install --upgrade numpy \
    && pip3 --no-cache-dir install --trusted-host buildsba.lco.gtn -r /var/www/apps/neoexchange/requirements.txt

# Download and build find_orb
RUN mkdir /tmp/git_find_orb \
    && cd /tmp/git_find_orb \
    && git clone https://github.com/Bill-Gray/lunar.git \
    && git clone https://github.com/Bill-Gray/sat_code.git \
    && git clone https://github.com/Bill-Gray/jpl_eph.git \
    && git clone https://github.com/Bill-Gray/find_orb.git

# Start a new shell and enable the Developer Toolset 7 toolchain so we get newer (7.3) g++
SHELL [ "scl", "enable", "devtoolset-7" ]
RUN cd /tmp/git_find_orb \
    && cd lunar && make && make install && cd .. \
    && cd jpl_eph && make && make install && cd .. \
    && cd lunar && make integrat && make install && cd .. \
    && cd sat_code && make && make install && cd .. \
    && cd find_orb && make && make install && cp ps_1996.dat elp82.dat /root/.find_orb && cd .. \
    && cp /root/bin/fo /usr/local/bin/ \
    && chmod 755 /root \
    && rm -rf /tmp/git_find_orb

# Copy operating system configuration files
COPY docker/ /

# Copy the LCO NEOexchange webapp files
COPY neoexchange /var/www/apps/neoexchange

# Copy default findorb config file
COPY neoexchange/photometrics/configs/environ.def /root/.find_orb/
RUN chmod 2775 /root/.find_orb

# Working directory should be the Django directory
WORKDIR /var/www/apps/neoexchange
