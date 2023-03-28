"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2016-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User, Permission
from django.contrib.auth.hashers import check_password
from django.utils.translation import gettext as _
import requests
import logging

from core.models import Proposal, ProposalPermission

logger = logging.getLogger(__name__)


class ValhallaBackend(object):
    """
    Authenticate against the Vahalla API.
    """

    def authenticate(self, request, username=None, password=None):
        return lco_authenticate(request, username, password)

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


def lco_authenticate(request, username, password):
    token = api_auth(settings.PORTAL_TOKEN_URL, username, password)
    profile, msg = get_profile(token)
    if msg:
        messages.info(request, msg)
    archivetoken = api_auth(settings.ARCHIVE_TOKEN_URL, username, password)
    if token and profile and archivetoken:
        username = profile[0]
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # Create a new user. There's no need to set a password
            # because Valhalla auth will always be used.
            user = User(username=username)
        user.token = token
        user.archive_token = archivetoken
        user.default_proposal = profile[2]
        user.save()
        # Finally add these tokens as session variables
        request.session['token'] = token
        request.session['archive_token'] = archivetoken
        return user
    return None


def api_auth(url, username, password):
    """
    Request authentication cookie from the Scheduler API
    """
    try:
        r = requests.post(url, data={'username': username, 'password': password}, timeout=20.0)
    except requests.exceptions.Timeout:
        msg = "Observing portal API timed out"
        logger.error(msg)
        return False
    except requests.exceptions.ConnectionError:
        msg = "Trouble with internet"
        logger.error(msg)
        return False

    if r.status_code in [200, 201]:
        logger.debug('Login successful for {}'.format(username))
        return r.json()['token']
    else:
        logger.error("Could not login {}: {}".format(username, r.json()['non_field_errors']))
        return False


def get_profile(token):
    url = settings.PORTAL_PROFILE_URL
    token = {'Authorization': 'Token {}'.format(token)}
    try:
        r = requests.get(url, headers=token, timeout=20.0)
    except requests.exceptions.Timeout:
        msg = "Observing portal API timed out"
        logger.error(msg)
        return False, _("We are currently having problems. Please bear with us")

    if r.status_code in [200, 201]:
        logger.debug('Profile successful')
        proposal = check_proposal_membership(r.json()['proposals'])
        if proposal:
            return (r.json()['username'], r.json()['tokens']['archive'], proposal), False
        else:
            logger.debug('No active proposal')
            return False, _("Sorry, you are not a member of an authorized proposal")
    else:
        logger.error("Could not get profile {}".format(r.content))
        return False, _("Please check your login details")


def check_proposal_membership(proposals):
    # Check user has a proposal we authorize
    proposals = [p['id'] for p in proposals if p['current'] is True]
    my_proposals = Proposal.objects.filter(code__in=proposals, active=True)
    if my_proposals:
        return my_proposals[0]
    else:
        return False


def parse_proposals(proposals):
    """
    Check if proposals user is attached to matches NEOx proposals
    """
    proposal_list = [p['code'] for p in proposals]
    neox_proposals = Proposal.objects.filter(active=True, code__in=proposal_list)
    if neox_proposals > 0:
        return True
    else:
        return False


def update_proposal_permissions(user, proposals):
    proposal_list = [p['code'] for p in proposals]
    inactive = ProposalPermission.objects.filter(user=user).exclude(proposal__code__in=proposal_list)
    inactive.delete()
    my_proposals = Proposal.objects.filter(proposalpermission__user=user, active=True).values_list('code', flat=True)
    for p in Proposal.objects.filter(code__in=proposal_list, active=True).exclude(code__in=my_proposals):
        pp = ProposalPermission(user=user, proposal=p)
        pp.save()
    return

def update_user_permissions(user, perm):
    if not isinstance(perm, Permission):
        try:
            app_label, codename = perm.split('.', 1)
        except ValueError:
            raise ValueError("For global permissions, first argument must be in"
                             " format: 'app_label.codename' (is %r)" % perm)
        perm = Permission.objects.get(content_type__app_label=app_label,
                                      codename=codename)
    user.user_permissions.add(perm)
    return
