from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.backends import ModelBackend
from django.conf import settings
from django.contrib.auth.models import Group
from oauthlib.oauth2 import LegacyApplicationClient
from requests_oauthlib import OAuth2Session
import json
import logging
from core.models import Proposal

logger = logging.getLogger(__name__)


def rbauth_login(email, password, request=None):
    client = LegacyApplicationClient(client_id=settings.CLIENT_ID)
    oauth = OAuth2Session(client=client)
    try:
        token = oauth.fetch_token(token_url=settings.RBAUTH_TOKEN_URL,
                            username=email,
                            password=password,
                            client_id=settings.CLIENT_ID,
                            client_secret=settings.CLIENT_SECRET)
        profile = oauth.get(settings.RBAUTH_PROFILE_API)
        profile = json.loads(profile.content)
        proposals = oauth.get(settings.RBAUTH_PROPOSAL_API)
        proposals = json.loads(proposals.content)
    except Exception, e:
        # User is not found
        logger.error(e)

        return None, None

    return profile, proposals


def checkUserObject(profile, proposals, password):
    # Logging in can only be done using email address if using RBauth
    try:
        user = User.objects.get(email=profile['email'])
        user.set_password(password)
        if user.first_name != profile['first_name']:
            user.first_name == profile['first_name']
        if user.last_name != profile['last_name']:
            user.last_name == profile['last_name']
        if user.email != profile['email']:
            user.email == profile['email']
        user.save()
    except User.DoesNotExist:
        # Check is user has any proposals matching NEOx
        has_proposals = parse_proposals(proposals)
        if has_proposals:
            name_count = User.objects.filter(username__startswith = profile['username']).count()
            if name_count > 0:
                username = '%s%s' % (profile['username'], name_count + 1)
            else:
                username = profile['username']
            user = User.objects.create_user(username,email=profile['email'])
            user.first_name = profile['first_name']
            user.last_name = profile['last_name']
            user.set_password(password)
            user.is_staff = True
            user.save()
        else:
            logger.info("Permission Denied to %s" % profile['email'])
            raise PermissionDenied
    return user


class LCOAuthBackend(ModelBackend):
    def authenticate(self, username=None, password=None, request=None):
        # This is only to authenticate with RBauth
        # If user cannot log in this way, the normal Django Auth is used
        profile, proposals = rbauth_login(username, password)
        if (profile):
            return checkUserObject(profile, proposals, password)

        return None

    def get_user(self, user_id):
        try:

            return User.objects.get(pk=user_id)
        except User.DoesNotExist:

            return None

def parse_proposals(proposals):
    '''
    Check if proposals user is attached to matches NEOx proposals
    '''
    proposal_list = [p['code'] for p in proposals]
    neox_proposals = Proposal.objects.filter(active=True, code__in=proposal_list)
    if neox_proposals > 0:
        return True
    else:
        return False
