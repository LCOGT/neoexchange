import requests
import sys

from django.conf import settings

ssl_verify = True
# Check if Python version is less than 2.7.9. If so, disable SSL warnings and SNI verification
if sys.version_info < (2,7,9):
    requests.packages.urllib3.disable_warnings()
    ssl_verify = False # Danger, danger !

def get_lcogt_headers(auth_url, username, password):
    #  Get the authentication token
    if 'archive' in auth_url:
        token = settings.ARCHIVE_TOKEN
    else:
        token = settings.PORTAL_TOKEN
    headers = {'Authorization': 'Token ' + token}


    return headers
