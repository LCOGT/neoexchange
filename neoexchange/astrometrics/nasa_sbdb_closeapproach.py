"""This code is to get information from NASA's JPL SBDB Close-Approach Data. This will produce a JSON file that can be manipulated."""

import urllib.request
import json
import logging
import fileinput
import numpy as np
import matplotlib.pyplot as plt

from astrometrics.albedo import asteroid_diameter 
"""
this gets Earth close-approach data for NEOs between the dates Jan. 1st, 1900 to Jan 1st, 2100 and is sorted by distance 
"""
logger = logging.getLogger(__name__)

def get_info(self):

    NASA_SBDB_url = 'https://ssd-api.jpl.nasa.gov/cad.api?body=Earth&date-min=1900-01-01&date-max=2100-01-01&sort=dist'

    sbdb_request = requests.get(NASA_SBDB_url)

    if sbdb_request.status_code() == requests.codes.bad:
        logger.error("There has been an Error")
    elif json.loads(sbdb_request)['count']== 0: 
        logger.error("Query too restrictive")
    else:    
        info = json.loads(sbdb_request)
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
        for objects in json['data']:
            des = line.split(', u')[0]
            iD = float(line.split(', u')[1])
            date = float(line.split(', u')[2])
            cal_date = line.slit(', u')[3]
            dist = float(line.split(', u')[4])
            min_d = float(line.split(', u')[5])
            max_d = float(line.split(', u')[6])
            vel = float(line.split(', u')[7])
            vel_inf = float(line.split(', u')[8])
            tsig = float(line.split(', u')[9])
            body = line.split(', u')[10]
            h = float(line.split(', u')[11])
            
            designation.append(des)
            orbit_id.append(iD)
            date_of_closeapproach(date)
            calender_date.append(cal_date)
            dist_of_closeapproach.append(dist)
            min_dist.append(min_d)
            max_dist.append(max_d)
            velocity.append(vel)
            velocity_massless.append(vel_inf)
            time_uncertainty.append(tsig)
            body_close_to.append(body)
            h_mag.append(h)
    return designation, orbit_id, date_of_closeapproach, distance_of_closeapproach, min_dist, max_dist, time_uncertainty, h_mag 

def size(self, mag=h_mag):
    '''this creates a list of diameters and uncertainties based on asteroid_diameter'''
    h = mag
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
        
def plotData(self):
    
    min_error = get_info[5]
    max_error = get_info[6]
    sizeerror = [min_error, max_error]
    x = get_info[8]
    y = get_info[4]
    fig, (ax0, ax1) = plt.subplots()
    ax0.errorbar(x, y, yerr=sizeerror, fmt='-o')
    ax0.set_title('Magnitude vs. Close Approach Distance of NEOs')
    
    n_bins = #count from json
    ax1.hist(x, n_bins, histtype='bar')
    ax1.set_title('
    
    
    
'''
{
  "signature":{"version":"1.1","source":"NASA/JPL SBDB Close Approach Data API"},
  "count":"2",
  "fields":["des","orbit_id","jd","cd","dist","dist_min","dist_max","v_rel","v_inf","t_sigma_f","h","fullname"],
  "data":[
    ["2007 JB21","9","2418800.878283280","1910-May-09 09:05","0.0020925812637796","0.000330379338764904","0.00489001931160697","7.59151917808528","7.4218978450753","00:25","25.4","       (2007 JB21)"],
    ["2012 BX34","16","2419429.176816497","1912-Jan-27 16:15","0.00224445877558233","0.00107169260360805","0.0791138808793694","9.53393503237496","9.40859414806313","1_00:16","27.6","       (2012 BX34)"]
  ]
}
'''
