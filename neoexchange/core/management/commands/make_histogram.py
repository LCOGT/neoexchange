"""
This code is for plotting diameter and rotational period values of NEOs on histograms and scatter plots.
The data used for plotting is stored from the JPL Horizons database.
This code was written and last edited by Isabel Kosic on August 16th, 2019 during a summer internship at LCO.
"""


from django.core.management.base import BaseCommand, CommandError
from core.models import Body
from core.models import PhysicalParameters
from astropy.table import Table
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colors
import matplotlib.ticker as ticker
from matplotlib.ticker import PercentFormatter
from matplotlib.ticker import ScalarFormatter
import math
from sys import exit
import logging

logger = logging.getLogger(__name__)



class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('param1', type=str, nargs='?', default='D', help="The first parameter that will be plotted.")
        parser.add_argument('param2', type=str, nargs='?', default='P', help="The second parameter that will be plotted.")

    def handle(self, *args, **options):
        self.stdout.write("=== Populating Bodies from JPL %s ===")
        
        param1 = options['param1']
        param2 = options['param2']
        value1 = PhysicalParameters.objects.filter(parameter_type=param1)
        value2 = PhysicalParameters.objects.filter(parameter_type=param2)

        try:
            plot_histogram(value1)
            plot_histogram(value2)
            plot_scatterplot_with_errorbars(value1, value2)
        except (ValueError, IndexError):
            logger.error('Problem plotting data.')    
    
def plot_histogram(data, title='', xlabel='', ylabel='', color=''):
    """Plots a histogram, with values on the x-axis, and percentages on the y-axis."""
    if not title:
        title = "{} Histogram ({} values)".format(data[0].get_parameter_type_display(), len(data.exclude(value=None)))
    if not xlabel:
        xlabel = '{} ({})'.format(data[0].get_parameter_type_display(), data[0].units)
    
    value_list = []
    for datum in data:
        if datum.value:
            if 'Frequency' in title:
                value_list.append(1/(datum.value*60*60))
            else:
                value_list.append(datum.value)
                           
    numofvalues = len(value_list)
    minbin = (min(value_list))
    maxbin = math.ceil(max(value_list))
    numofbins = round(np.sqrt(len(value_list)))
    Bins = 2 * math.ceil(numofbins)
    diffbin = round((maxbin - minbin)/numofbins)
    
    plt.hist(value_list, bins=Bins, alpha=1, histtype='bar', align='mid', rwidth=1, color='skyblue', edgecolor='black')
    plt.title(title)
    #plt.xscale('log')
    #plt.yscale('log')
    plt.gca().yaxis.set_major_formatter(PercentFormatter(xmax=numofvalues))
    #plt.gca().xaxis.set_major_formatter(ticker.FuncFormatter(lambda x,pos: ('{{:.{:1d}f}}'.format(int(np.maximum(-np.log10(x),0)))).format(x)))
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xticks()
    plt.tick_params(axis = 'x', rotation = 45)
    plt.show()


def plot_histogram_zoomin(data, title='', xlabel='', ylabel='', color=''):
    """Plots a histogram that zooms in on lower values."""
    if not title:
        title = "{} Histogram ({} values)".format(data[0].get_parameter_type_display(), len(data))
    if not xlabel:
        xlabel = '{} ({})'.format(data[0].get_parameter_type_display(), data[0].units)
    
    value_list_zoom = []
    for datum in data:
        if datum.value:
            if datum.value <= 1:
                value_list_zoom.append(datum.value)
                
    numofvalues_zoom = len(value_list_zoom)
    minbin = (min(value_list_zoom))
    maxbin = math.ceil(max(value_list_zoom))
    numofbins = round(np.sqrt(len(value_list_zoom)))
    Bins = 3 * math.ceil(numofbins)
    diffbin = round((maxbin - minbin)/numofbins)

    plt.hist(value_list_zoom, bins=Bins, alpha=1, histtype='bar', align='mid', rwidth=1, color='skyblue', edgecolor='black')
    plt.title(title)
    #plt.xscale('log')
    #plt.yscale('log')
    plt.gca().yaxis.set_major_formatter(PercentFormatter(xmax=numofvalues_zoom))
    #plt.gca().xaxis.set_major_formatter(ticker.FuncFormatter(lambda x,pos: ('{{:.{:1d}f}}'.format(int(np.maximum(-np.log10(x),0)))).format(x)))
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xticks()
    plt.tick_params(axis = 'x', rotation = 45)
    plt.show()   
         

def plot_scatterplot_with_errorbars(value1, value2):
    """Scatter plot of two sets of values (with error bars)."""
    value1_nlist = []
    for v in value1:
        if v.value:
            value1_nlist.append(v.body.name)

    value2_nlist = []
    for v in value2:
        if v.value:
            value2_nlist.append(v.body.name)

    overlap_list = list(set(value1_nlist) & set(value2_nlist))

    value1_values = []
    value2_values = []
    value1_errors = []
    value2_errors = []
    for o in overlap_list:
        x = value1.filter(body__name=o)
        y = value2.filter(body__name=o)
        value1_values.append(x[0].value)
        value2_values.append(y[0].value)
        if x[0].error != None:
            value1_errors.append(x[0].error)
        elif x[0].error == None:
            value1_errors.append(0)
        if y[0].error != None:
            value2_errors.append(y[0].error)
        elif y[0].error == None:
            value2_errors.append(0)
    
    xmin = min(value1_values)
    xmax = math.ceil(max(value1_values))
    xbuffer = (xmax - xmin) * 0.2
    ymin = min(value2_values)
    ymax = math.ceil(max(value2_values))
    ybuffer = (ymax - ymin) * 0.2
    xmax += xbuffer        
    ymax += ybuffer
    if xmin - xbuffer <= 0:
        xmin -= 0.2 * (xmin)
    else:
        xmin -= xbuffer
    if ymin - ybuffer <= 0:
        ymin -= 0.2 * (ymin)
    else:
        ymin -= ybuffer    
    
    plt.xlim(xmin, xmax)
    plt.ylim(ymin, ymax)
    plt.title("{} vs {}".format(value1[0].get_parameter_type_display(), value2[0].get_parameter_type_display()))
    plt.xlabel('{} ({})'.format(value1[0].get_parameter_type_display(), value1[0].units))
    plt.ylabel('{} ({})'.format(value2[0].get_parameter_type_display(), value2[0].units))
    plt.xscale('log')
    plt.yscale('log')
    plt.gca().xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: '{:g}'.format(x)))
    plt.gca().yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: '{:g}'.format(y))) 
    plt.gca().invert_yaxis()
    plt.errorbar(value1_values, value2_values, xerr=value1_errors, yerr=value2_errors, fmt='+', ecolor='red')  
    plt.xticks()
    plt.tick_params(axis = 'x', rotation = 45)
    plt.show()
