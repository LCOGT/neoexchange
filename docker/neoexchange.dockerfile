#
# neoexchange dockerfile
#
FROM lcogtwebmaster/lcogt:webbase
MAINTAINER LCOGT <webmaster@lcogt.net>
RUN yum -y update; yum clean all

ADD . /var/www/apps/neoexchange
WORKDIR /var/www/apps/neoexchange
RUN cat docker/config/nginx.conf | envsubst '$PREFIX $neoexchange_UWSGI_PORT_8001_TCP_ADDR' > /etc/nginx/nginx.conf

RUN pip install -r pip-requirements.txt
RUN python manage.py collectstatic --noinput;

ENV PYTHONPATH /var/www/apps
ENV DJANGO_SETTINGS_MODULE neoexchange.settings
ENV BRANCH ${BRANCH}
ENV BUILDDATE ${BUILDDATE}
ENV PREFIX ${PREFIX}

EXPOSE 8000
EXPOSE 8001
