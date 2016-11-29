# Create your tasks here
from __future__ import absolute_import, unicode_literals
from celery import shared_task
from celery.schedules import crontab
from celery.decorators import periodic_task

import os
from datetime import datetime

from astrometrics.sources_subs import imap_login, fetch_NASA_targets, fetch_arecibo_targets,  fetch_goldstone_targets, random_delay
from core.views import update_MPC_orbit

from django.db.models import Q

import logging

logger = logging.getLogger(__name__)


@periodic_task(run_every=(crontab(minute='20,50')))
def update_neocp_data():
    #Check NEOCP for objects in need of follow up
    logger.debug("==== Fetching NEOCP targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
    neocp_page = fetch_NEOCP()
    obj_ids = parse_NEOCP_extra_params(neocp_page)
    logger.debug("==== Found %s NEOCP targets ====" % len(obj_ids))
    for obj_id in obj_ids:
        obj_name = obj_id[0]
        obj_extra_params = obj_id[1]
        logger.debug("Reading NEOCP target %s" % obj_name)
        resp = update_NEOCP_orbit(str(obj_name), obj_extra_params)
        if resp:
            logger.debug(resp)
        resp = update_NEOCP_observations(str(obj_name), obj_extra_params)
        if resp:
            logger.debug(resp)

@periodic_task(run_every=(crontab(minute=27, hour=5)))
def fetch_arecibo_targets():
    # Fetch Arecibo target list for the current year
    logger.debug("==== Fetching Arecibo targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
    radar_targets = fetch_arecibo_targets()
    for obj_id in radar_targets:
        logger.debug("Reading Arecibo target %s" % obj_id)
        update_MPC_orbit(obj_id, origin='A')
        # Wait between 10 and 20 seconds
        delay = random_delay(10, 20)
        logger.debug("Slept for %d seconds" % delay)

@periodic_task(run_every=(crontab(hour=5,minute=2)))
def fetch_goldstone_targets():
    logger.debug("==== Fetching Goldstone targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
    radar_targets = fetch_goldstone_targets()
    for obj_id in radar_targets:
        logger.debug("Reading Goldstone target %s" % obj_id)
        update_MPC_orbit(obj_id, origin='G')
        # Wait between 10 and 20 seconds
        delay = random_delay(10, 20)
        logger.debug("Slept for %d seconds" % delay)

@periodic_task(run_every=(crontab(minute=42, hour='5,16')))
def fetch_NASA_targets():
    username = os.environ.get('NEOX_EMAIL_USERNAME','')
    password = os.environ.get('NEOX_EMAIL_PASSWORD','')
    if username != '' and password != '':
        logger.debug("==== Fetching NASA/ARM targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        mailbox = imap_login(username, password)
        if mailbox:
            NASA_targets = fetch_NASA_targets(mailbox, folder="NASA-ARM")
            for obj_id in NASA_targets:
                logger.debug("Reading NASA/ARM target %s" % obj_id)
                update_MPC_orbit(obj_id, origin='N')
                # Wait between 10 and 20 seconds
                delay = random_delay(10, 20)
                logger.debug("Slept for %d seconds" % delay)

            mailbox.close()
            mailbox.logout()

@periodic_task(run_every=(crontab(minute=30, hour='0,4,8,12,16,20')))
def update_crossids():
    logger.debug("==== Updating Cross-IDs %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
    objects = fetch_previous_NEOCP_desigs()
    for obj_id in objects:
        resp = update_crossids(obj_id, dbg=False)
        if resp:
            msg = "Updated crossid for %s" % obj_id
            logger.debug(msg)
