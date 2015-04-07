#
# webbase image dockerfile
#
FROM centos:centos6
MAINTAINER LCOGT <webmaster@lcogt.net>
RUN yum -y update; yum clean all
RUN yum -y install epel-release; yum clean all
RUN yum -y install nginx; yum clean all
RUN yum -y install python-pip; yum clean all
RUN yum -y install mysql-devel; yum clean all
RUN yum -y groupinstall "Development Tools"; yum clean all
RUN yum -y install python-devel; yum clean all
RUN pip install pip==1.3;  pip install uwsgi==2.0.8

ENV LC_ALL en_US.UTF-8
ENV LANG en_US.UTF-8
