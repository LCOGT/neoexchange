import requests
import sys

ssl_verify = True
# Check if Python version is less than 2.7.9. If so, disable SSL warnings and SNI verification
if sys.version_info < (2,7,9):
    requests.packages.urllib3.disable_warnings()
    ssl_verify = False # Danger, danger !

def get_lcogt_headers(auth_url, username, password):
    #  Get the authentication token
    response = requests.post(auth_url,
        data = {
                'username': username,
                'password': password
               }, verify=ssl_verify).json()

    try:
        token = response.get('token')

        # Store the Authorization header
        headers = {'Authorization': 'Token ' + token}
    except TypeError:
        headers = None

    return headers

def get_telescope_states(telstates_url='http://valhalla.lco.gtn/api/telescope_states/'):

    try:
        response = requests.get(telstates_url).json()
    except ValueError:
        response = {}

    return response
