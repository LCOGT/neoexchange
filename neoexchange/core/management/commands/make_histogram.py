""""""




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






class Command(BaseCommand):
    #table = Table.read('NEOs.csv')

    def handle(self, *args, **options):
        self.stdout.write("=== Populating Bodies from JPL %s ===")

       
    def plot_histogram(data, title='', xlabel='', ylabel='', color=''):

        value_list = []
        for datum in data:
            if datum.value:
                if 'Frequency' in title:
                    value_list.append(1/(datum.value*60*60))
                else:
                    value_list.append(datum.value)
                
                        
        numofvalues = len(value_list)
        print(numofvalues)
        
        minbin = (min(value_list))
        print(minbin)
        maxbin = math.ceil(max(value_list))
        print(maxbin)
        numofbins = round(np.sqrt(len(value_list)))
        print(numofbins)
        Bins = 2 * math.ceil(numofbins)
        diffbin = round((maxbin - minbin)/numofbins)
        print(diffbin)
        
        plt.hist(value_list, bins=Bins, alpha=1, histtype='bar', align='mid', rwidth=1, color='skyblue', edgecolor='black')
        plt.title(title)
        #plt.xscale('log')
        plt.yscale('log')
        plt.gca().yaxis.set_major_formatter(PercentFormatter(xmax=numofvalues))
        #plt.gca().xaxis.set_major_formatter(ticker.FuncFormatter(lambda x,pos: ('{{:.{:1d}f}}'.format(int(np.maximum(-np.log10(x),0)))).format(x)))
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.xticks()
        plt.tick_params(axis = 'x', rotation = 45)
        plt.show()


    def plot_histogram_zoomin(data, title='', xlabel='', ylabel='', color=''):

        value_list_zoom = []
        for datum in data:
            if datum.value:
                if datum.value <= 1:
                    value_list_zoom.append(datum.value)
                    
        numofvalues_zoom = len(value_list_zoom)
        print(numofvalues_zoom)
        
        minbin = (min(value_list_zoom))
        print(minbin)
        maxbin = math.ceil(max(value_list_zoom))
        print(maxbin)
        numofbins = round(np.sqrt(len(value_list_zoom)))
        print(numofbins)
        Bins = 3 * math.ceil(numofbins)
        diffbin = round((maxbin - minbin)/numofbins)
        print(diffbin)
        
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
        
        
    def plot_histogram_2D(data1, data2, title='', xlabel='', ylabel='', color=''):

        value_list1 = []
        for datum1 in data1:
            if datum1.value:
                value_list1.append(datum1.value)
        value_list2 = []
        for datum2 in data2:
            if datum2.value:
                value_list2.append(datum2.value)
        
                     
        numofvalues1 = len(value_list1)
        print('numofvalues1', numofvalues1)
        numofvalues2 = len(value_list2)
        print('numofvalues2', numofvalues2)

        
        minbin1 = math.floor(min(value_list1))
        print('minbin1', minbin1)
        maxbin1 = math.ceil(max(value_list1))
        print('maxbin1', maxbin1)
        numofbins1 = round(np.sqrt(len(value_list1)))
        print('numofbins1', numofbins1)
        Bins1 = math.ceil(numofbins1)
        print('Bins1', Bins1)
        diffbin1 = round((maxbin1 - minbin1)/numofbins1)
        print('diffbin1', diffbin1)
        
        minbin2 = math.floor(min(value_list2))
        print('minbin2', minbin2)
        maxbin2 = math.ceil(max(value_list2))
        print('maxbin2', maxbin2)
        numofbins2 = round(np.sqrt(len(value_list2)))
        print('numofbins2', numofbins2)
        Bins2 = math.ceil(numofbins2)
        print('Bins2', Bins2)
        diffbin2 = round((maxbin2 - minbin2)/numofbins2)
        print('diffbin2', diffbin2)
        
        #2D figure with Diameter and Rotational Period
        plt.hist2d(value_list1, value_list2, bins=[30, 35], norm=colors.LogNorm())
        #for white area, add ..., norm=colors.LogNorm())
        plt.title(title)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.xticks()
        plt.yticks()
        plt.show()    
        
        
        
    #print(Body.objects.filter().count())
    diameters = PhysicalParameters.objects.filter(parameter_type='D').exclude(body=13)
    periods = PhysicalParameters.objects.filter(parameter_type='P').exclude(body=13)
    body_names = Body.objects.filter() #.exclude(body=13)
    
    #plot_histogram(diameters, title="NEO Diameter Histogram", xlabel='Diameter (km)', ylabel='')
    #plot_histogram(periods, title="Rotation Period Histogram", xlabel='Rotation Period (hours)')
    #plot_histogram(periods, title="Frequency Histogram", xlabel='Frequency (Hz)')
    #plot_histogram_zoomin(diameters, title='NEO Diameter Histogram (up to 1km)', xlabel='Diameter (km)', ylabel='', color='')
    
    diameter_vlist = []
    diameter_nlist = []
    for d in diameters:
        if d.value:
            #print(d, ',', d.value, ',', d.body.name)
            diameter_vlist.append(d.value)
            diameter_nlist.append(d.body.name)
    #print(diameter_list)
    #print(len(diameter_list))
    
    period_vlist = []
    period_nlist = []
    for p in periods:
        if p.value:
            #print(p, ',', p.value, ',', p.body.name)
            period_vlist.append(p.value)
            period_nlist.append(p.body.name)
    #print(period_list)        
    #print(len(period_list))
    
    overlap_list = list(set(diameter_nlist) & set(period_nlist))
    #print(overlap_list)
    print(len(overlap_list))

    for o in overlap_list:
        x = diameters.filter(body__name=o)
        print(x)
        y = periods.filter(body__name=o)
        




    
    #plot_histogram_2D(diameters, periods, title="Diameter vs Rotation Period", xlabel='Diameter (km)', ylabel='Rotation Period (hrs)')
    
    
    
    
    
    
    
    
    


