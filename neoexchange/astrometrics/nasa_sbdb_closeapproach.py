"""This code is to get information from NASA's JPL SBDB Close-Approach Data. This will produce a JSON file that can be manipulated."""

import urllib.request


"""
this gets Earth close-approach data for NEOs between the dates Jan. 1st, 1900 to Jan 1st, 2100 and is sorted by distance 
"""
NASA_SBDB_url = 'https://ssd-api.jpl.nasa.gov/cad.api?body=Earth&date-min=1900-01-01&date-max=2100-01-01&sort=dist'

files = {'file': ('sbdb_July2017.json', open('sbdb_July2017.json', )}

sbdb_request = requests.get(NASA_SBDB_url)
sbdb_request.json()
