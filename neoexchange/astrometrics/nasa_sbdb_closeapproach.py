"""This code is to get information from NASA's JPL SBDB Close-Approach Data. This will produce a JSON file that can be manipulated."""

import requests
import json
import logging
import fileinput
import numpy as np
import matplotlib.pyplot as plt

from albedo import asteroid_diameter 
"""
this gets Earth close-approach data for NEOs between the dates Jan. 1st, 1900 to Jan 1st, 2100 and is sorted by distance 
"""
logger = logging.getLogger(__name__)

def get_info(self, url='https://ssd-api.jpl.nasa.gov/cad.api?body=Earth&date-min=1900-01-01&date-max=2100-01-01&sort=dist'):

    sbdb_request = requests.get(url)

    if sbdb_request.status_code() == requests.codes.bad:
        logger.info("Bad Request")
    elif sbdb_request.status_code() == requests.codes.error:
        logger.info("JPL Internal Server Error")
    elif json.loads(sbdb_request)['count']== 0: 
        logger.info("Query too restricted")
    else:    
        logger.info("Request Good")
        info = json.loads(sbdb_request)
        print info
        designation = []
        orbit_id = []
        date_of_closeapproach = []
        calender_date =[]
        dist_of_closeapproach = []
        min_dist = []
        max_dist = []
        velocity = []
        velocity_massless = []
        time_uncertainty = []
        body_close_to = []
        h_mag = [] 
        name = []
        for objects in info['data']:
            designation.append(objects[0])
            orbit_id.append(objects[1])
            date_of_closeapproach(objects[2])
            calender_date.append(objects[3])
            dist_of_closeapproach.append(objects[4])
            min_dist.append(objects[5])
            max_dist.append(objects[6])
            velocity.append(objects[7])
            velocity_massless.append(objects[8])
            time_uncertainty.append(objects[9])
            body_close_to.append(objects[10])
            h_mag.append(objects[11])
            name.append(objects[12])
        neo_info = {'count':info['count'],'des':designation, 'iD':orbit_id, 'date':date_of_closeapproach, 'dist':dist_of_closeapproach, 'mind':min_dist, 'maxd':max_dist, 'vel':velocity, 'tsig':time_uncertainty, 'h_mag':h_mag, 'name':name}  
        return neo_info

def size(self, info=get_info):
    '''this creates a list of diameters and uncertainties based on asteroid_diameter'''
    h = info[h_mag]
    size_avg = []
    size_min = []
    size_max = []
    for mag in h:
        diameter = asteroid_diameter(a=.17, h=mag)
        min_diameter = asteroid_diameter(a=.01, h=mag)
        max_diameter = asteroid_diameter(a=.60, h=mag)
        size_avg.append(diameter)
        size_min.append(min_diameter)
        size_max.append(max_diameter)
    neo_size = {'dia':size_avg, 'mindia':size_min, 'maxdia':size_min}
    return neo_size
        
def plotData(self, info=get_info, size=size):
    fig, (ax0, ax1, ax2, ax3, ax4) = plt.subplots()
    
    
    min_error = info[mind]
    max_error = info[maxd]
    dist_error = [min_error, max_error]
    x = info[h_mag]
    y = info[dist]
    
    ax0.errorbar(x, y, yerr=dist_error, fmt='-o')
    ax0.set_title('Magnitude vs. Close Approach Distance of NEOs')
    
    min_diaerror = size[mindia]
    max_diaerror = size[maxdia]
    dia_error = [mindia, maxdia]
    w = size[dia]
    
    ax1.errorbar(w, y, werr=dia_error, yerr=dist_error, fmt='-o')
    ax1.set_title('Approximate Diameter vs. Close Approach Distance of NEOs')
    
    
    n_bins = info[count]
    ax2.hist(w, n_bins, histtype='bar')
    ax2.set_title('Number of NEOs that make a Close Approach vs. Approximate Diameter')
    
    v = info[vel]
    ax3.errorbar(v, y, yerr=dist_error, fmt='-o')
    ax3.set_title('Velocity vs. Close Approach Distance of NEOs')
    
    ax4.scatter(x, v)
    ax4.set_title('Velocity vs. Magnitude')
    
    plt.show()
