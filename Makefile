#-----------------------------------------------------------------------------------------------------------------------
# neoexchange docker image makefile
#
# 'make' will create the docker image needed to run the neoexchange app:
#    lcogtwebmaster/lcogt:neoexchange_$BRANCH
#
# where $BRANCH is the git branch name presently in use.
#
# Once built, this image can be pushed up the docker hub repository via 'make install',
# and can then be run via something like:
#
# docker run -d -p 8200:8200 -p 8201:8201 --name=neoexchange lcogtwebmaster/lcogt:neoexchange_$BRANCH
#
# at which point nginx will be exposed on the host at port 8100
# and uwsgi will be exposed on the host at port 8101 (optional, leave out the -p 8101:8101 argument if you don't need it)
#
# Ira W. Snyder
# Doug Thomas
# LCOGT
#
#-----------------------------------------------------------------------------------------------------------------------

NAME := lcogtwebmaster/lcogt
BRANCH := $(shell git rev-parse --abbrev-ref HEAD)
BUILDDATE := $(shell date +%Y%m%d%H%M)
TAG1 := neoexchange_$(BRANCH)

.PHONY: all neoexchange login install

all: neoexchange

login:
	docker login --username="lcogtwebmaster" --password="lc0GT!" --email="webmaster@lcogt.net"

neoexchange:
	export BUILDDATE=$(BUILDDATE) && \
	export BRANCH=$(BRANCH) && \
	cat docker/neoexchange.dockerfile | /usr/local/opt/gettext/bin/envsubst '$$BRANCH $$BUILDDATE' > Dockerfile
	docker build -t $(NAME):$(TAG1) --rm .
	rm -f Dockerfile

install: login
	@if ! docker images $(NAME) | awk '{ print $$2 }' | grep -q -F $(TAG1); then echo "$(NAME):$(TAG1) is not yet built. Please run 'make'"; false; fi
	docker push $(NAME):$(TAG1)
