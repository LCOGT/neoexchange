from sys import exit
from datetime import datetime
from math import exp, log10, tan, radians

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import leastsq

from core.models import Body, SourceMeasurement

class Command(BaseCommand):

    help = 'Plot phase curve for specified object'

    def add_arguments(self, parser):
        parser.add_argument('body', type=str, help='Name of body to analyze')
        parser.add_argument('-H', type=float, help='H magnitude value')
        parser.add_argument('-G', type=float, default=0.15, help='G parameter')

    def residuals(self, params, y, x):
        err = y - self.compute_phase_function(x, params)
        return err

    def compute_phase_function(self, beta, params):

        phi1 = np.exp(-3.33 * (np.tan(beta/2.0))**0.63)
        phi2 = np.exp(-1.87 * (np.tan(beta/2.0))**1.22)
        mag = params[0] - 2.5 * np.log10((1.0-params[1])*phi1 + params[1]*phi2)

        return mag

    def fit_hg(self, data, degrees=True):
        xval = np.radians(data[:, 0]) if degrees else data[:, 0]
        yval = data[:, 1]

        pname = (['H','G'])
        params0 = np.array([self.H, self.G])
        plsq = leastsq(self.residuals, params0, args=(yval, xval), maxfev=2000)
        #
        # The sum of the residuals
        #
        resid = sum(np.sqrt((yval-self.compute_phase_function(xval,plsq[0]))**2))
        return plsq[0], resid

    def plot_phase_curve(self, measures, colors='r', title='', sub_title=''):
        phases = [x[0] for x in measures]
        mags = [x[1] for x in measures]
        mag_errs = [x[2] for x in measures]

        fig, ax = plt.subplots()
        ax.plot(phases, mags, color=colors, marker='.', linestyle=' ')
        ax.errorbar(phases, mags, yerr=mag_errs, color=colors, linestyle=' ')
        ax.invert_yaxis()
        xmin, xmax = ax.get_xlim()
        ax.set_xlim(0, xmax)
        # Compute and plot phase function
        phase_angles = np.linspace(0, xmax, 100)
        func_mags = self.compute_phase_function(np.radians(phase_angles), (self.H, self.G))
        plt.plot(phase_angles, func_mags, color='k', linestyle='-')
        ax.set_xlabel('Phase angle')
        ax.set_ylabel('Magnitude')
        fig.suptitle(title)
        ax.set_title(sub_title)
        ax.minorticks_on()
        plt.savefig("phasecurve.png")
        plt.show()

        return

    def handle(self, *args, **options):

        self.stdout.write("==== Phase curve building %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))

        name = options['body']
        try:
            body = Body.objects.get(Q(provisional_name__exact=name) | Q(provisional_packed__exact=name) | Q(name__exact=name))
        except Body.DoesNotExist:
            self.stdout.write("Body does not exist")
            exit(-1)
        except Body.MultipleObjectsReturned:
            self.stdout.write("Multiple Bodies found")
            exit(-1)

        self.H = options['H']
        self.G = options['G']

        self.stdout.write("Processing %s" % body.current_name())
        srcmeas = SourceMeasurement.objects.filter(body=body)
        self.stdout.write("Found %d SourceMeasurements for %s" % (srcmeas.count(), body.current_name()))

        phase_angle_meas = []
        for src in srcmeas:
            phase_angle = body.compute_body_phase_angle(src.frame.midpoint, src.frame.sitecode)
            mag_corr = body.compute_body_mag_correction(src.frame.midpoint, src.frame.sitecode)
            print(phase_angle, mag_corr)
            phase_angle_meas.append((phase_angle, src.obs_mag-mag_corr, src.err_obs_mag))

        plottitle = "Phase curve for {}".format(body.current_name())
        self.plot_phase_curve(phase_angle_meas, title=plottitle)
