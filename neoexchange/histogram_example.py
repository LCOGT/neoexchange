from django.core.management.base import BaseCommand, CommandError
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colors
from matplotlib.ticker import PercentFormatter
from core.models import PhysicalParameters
from sys import exit
import math




if __name__ == '__main__':
    diameters = PhysicalParameters.objects.filter(parameter_type='D')
    periods = PhysicalParameters.objects.filter(parameter_type='P')

    plot_histogram(diameters, xlabel='Diameter (km)')
    plot_histogram(periods, xlabel='Period (hours)')
    print(diameters)

def plot_histogram(data, xlabel='', ylabel='', color=''):

    #For 1D histogram

    #random_values = np.random.randn(50)
    #value1 = [6, 5, 7, 15.75, 89, 56, 22, 8, 44, 33, 55, 78, 31, 13, 3, 65, 50]
    #value2 = [12, 13, 87, 59, 68, 43, 93, 4.002, 0.01, 55, 33, 11, 77, 99, 23, 42, 42.5]
    #diameter = np.random.randint(0, 1000, 1000)
    #rot_period = np.random.randint(4, 30, 1000)


    
    #Diameter figure
    minbind = math.floor(min(diameter))
    maxbind = math.ceil(max(diameter))
    numofbinsd = 100
    diffbind = round((maxbind - minbind)/numofbinsd)
    Binsd = range(0, maxbind, diffbind)
    #print('minbin = ', minbind, ',', 'maxbin = ', maxbind, ',', 'diffbin = ', diffbind, ',', 'Bins = ', Binsd)
    plt.figure(1)
    plt.hist(diameter, bins=Binsd, alpha=1.0, histtype='bar', align='mid', rwidth=1, color='pink', edgecolor='black')
    plt.title("Diameter Histogram")
    plt.xlabel("Diameter (kilometers)")
    plt.ylabel("Number of values in each bin")
    plt.xticks()
    plt.tick_params(axis = 'x', rotation = 45)
    plt.show()

    #Rotational period figure
    minbinrp = math.floor(min(rot_period))
    maxbinrp = math.ceil(max(rot_period))
    numofbinsrp = 20
    diffbinrp = round((maxbinrp - minbinrp)/numofbinsrp)
    #print(diffbinrp)
    #Diffbinrp = np.around(diffbinrp, decimals = 2)
    #print(Diffbinrp)
    Binsrp = range(3, maxbinrp, diffbinrp)
    #print('minbin = ', minbinrp, ',', 'maxbin = ', maxbinrp, ',', 'diffbin = ', diffbinrp, ',', 'Bins = ', Binsrp)
    plt.figure(2)
    plt.hist(rot_period, bins=Binsrp, alpha=1, histtype='bar', align='mid', rwidth=1, color='skyblue', edgecolor='black')
    plt.title("Rotational Period Histogram")
    plt.xlabel("Rotational Period (hours)")
    plt.ylabel("Number of values in each bin")
    plt.xticks(Binsrp)
    plt.tick_params(axis = 'x', rotation = 45)
    plt.show()

    #2D figure with Diameter and Rotational Period
    plt.figure(3)
    plt.hist2d(diameter, rot_period, bins=[Binsd, Binsrp])
    #for white area, add ...Binsrp], norm=colors.LogNorm())
    plt.title("Diameter vs Rotational Period (2D Histogram)")
    plt.xlabel("Diameter (kilometers)")
    plt.ylabel("Rotational Period (hours)")
    plt.xticks()
    plt.yticks(Binsrp)
    plt.show()



    exit()
    #======================================================
    np.random.seed(19980121)
    N_points = 100000
    n_bins = 20
    x = np.random.randn(N_points)
    y = .4 * x + np.random.randn(100000) + 5

    fig, axs = plt.subplots(1, 2, tight_layout=True)
    N, bins, patches = axs[0].hist(x, bins=n_bins)
    fracs = N / N.max()
    norm = colors.Normalize(fracs.min(), fracs.max())
    for thisfrac, thispatch in zip(fracs, patches):
        color = plt.cm.viridis(norm(thisfrac))
        thispatch.set_facecolor(color)
    axs[1].hist(x, bins=n_bins, density=True)
    axs[1].yaxis.set_major_formatter(PercentFormatter(xmax=1))

    #2D
    fig, ax = plt.subplots(tight_layout=True)
    hist = ax.hist2d(x, y)

    fig, axs = plt.subplots(3, 1, figsize=(5, 15), sharex=True, sharey=True, tight_layout=True)
    axs[0].hist2d(x, y, bins=40)
    axs[1].hist2d(x, y, bins=40, norm=colors.LogNorm())
    axs[2].hist2d(x, y, bins=(80, 10), norm=colors.LogNorm())


    #ORIGINAL CODING OUTLINE (WORKS)
    ##figure1
    #minbin1 = math.floor(min(value1))
    #maxbin1 = math.ceil(max(value1))
    #numofbins1 = 20 #change as needed
    #diffbin1 = round((maxbin1 - minbin1)/numofbins1)
    #Bins1 = range(0, round(maxbin1+10, -1), diffbin1)
    ##print('minbin1 = ', minbin1, ',', 'maxbin1 = ', maxbin1, ',', 'diffbin1 = ', diffbin1, ',', 'Bins1 = ', Bins1)
    #plt.figure(1)
    #plt.hist(value1, bins=Bins1, alpha=1.0, histtype='bar', align='mid', rwidth=1, color='darkmagenta', edgecolor='black')
    #plt.title("Value1")
    #plt.xlabel("values (bins)")
    #plt.ylabel("# of values in each bin")
    #plt.xticks(Bins1)
    #plt.show()

    ##figure2
    #minbin2 = math.floor(min(value2))
    #maxbin2 = math.ceil(max(value2))
    #numofbins2 = 20 #change as needed
    #diffbin2 = round((max(value2) - min(value2))/numofbins2)
    #Bins2 = range(0, round(maxbin2+10, -1), diffbin2)
    ##print('minbin2 = ', minbin2, ',', 'maxbin2 = ', maxbin2, ',', 'diffbin2 = ', diffbin2, ',', 'Bins2 = ', Bins2)
    #plt.figure(2)
    #plt.hist(value2, bins=Bins2, alpha=1.0, histtype='bar', align='mid', rwidth=1, color='pink', edgecolor='black')
    #plt.title("Value2")
    #plt.xlabel("values (bins)")
    #plt.ylabel("# of values in each bin")
    #plt.xticks(Bins2)
    #plt.show()

    ##2D figure
    #plt.figure(3)
    #plt.hist2d(value1, value2, bins=[Bins1, Bins2])
    #plt.title("2D Histogram")
    #plt.xlabel("value1")
    #plt.ylabel("value2")
    #plt.xticks(Bins1)
    #plt.yticks(Bins2)
    #plt.show()


    #TRASH CODE
    axs[0].yaxis.set_major_formatter(PercentFormatter(xmax=10))

    x = np.random.normal(size = 1000)
    pyplot.hist(diameter, normed=True, bins=3)
    pyplot.ylabel('rotation_period')
    pyplot.show()

    #axes.set_xlabel('values (bins)')
    #axes.set_ylabel('# of values in each bin')

    #plt.xlabel('x-values (of bins)')
    #plt.ylabel('# of values in each bin')

    #plt.xlabel('y-values (of bins)')
    #plt.ylabel('# of values in each bin')

    #Generate a normal distribution, center at x=0 and y=5
    #x = np.random.randn(N_points) #centers at x=0
    #y = 0.4 * x + 5 #centers xaxis = 5
    #z = 2 * x
      
    fig, axes = plt.subplots(1, 2, sharex=False, sharey=False, tight_layout=True)

    axes[0].hist(value1, bins=n1_bins)
    axes[1].hist(value2, bins=n2_bins)

    #N1_points = len(value1)
    #N2_points = len(value2)
    #n1_bins = round(N1_points * 0.5, 1)
    #n2_bins = round(N2_points * 0.5, -1)
      
