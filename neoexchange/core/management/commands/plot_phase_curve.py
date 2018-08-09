from sys import exit
from datetime import datetime
from math import exp, log10, tan

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import leastsq
from numpy.linalg import lstsq as solve_leastsq, inv

from core.models import Body, SourceMeasurement

class Command(BaseCommand):

    help = 'Plot phase curve for specified object'

    def add_arguments(self, parser):
        parser.add_argument('body', type=str, help='Name of body to analyze')
        parser.add_argument('-H', type=float, help='H magnitude value')
        parser.add_argument('-G', type=float, default=0.15, help='G parameter')

    def a1a2_to_HG(self, params):
        res = np.zeros(2)
        x = params.sum()
        res[0] = -2.5 * log10(x)
        res[1] = params[1] / params[0]
        return res

    def fit_hg_matrix(self, data, weight=None, degrees=True):
        Ndata = data.shape[0]
        Ncols = data.shape[1]        

        xval = np.radians(data[:, 0]) if degrees else data[:, 0]
        yval = 10**(-0.4 * data[:, 1])

        if weight is not None:
            if isinstance(weight, Number):
                errors = np.zeros(Ndata) + weight
            else:
                errors = weight
        else:
            errors = np.zeros(Ndata)+0.03
        sigmas = yval * (10**(0.4*errors) - 1)
        Amatrix = np.matrix(np.zeros((Ndata, 3)))
        G0 = 0.15
        for i in range(Ndata):
            phi1 = exp(-3.33 * (tan(xval[i]/2.0))**0.63)
            phi2 = exp(-1.87 * (tan(xval[i]/2.0))**1.22)
            Gamma1 = phi1 
            Gamma2 = phi2
            print(xval[i], Gamma1, Gamma2)
            Amatrix[i, :] = np.array([1.0/sigmas[i], Gamma1/sigmas[i],  Gamma2/sigmas[i]])
        print(Amatrix)
        yval = 1/(10**(0.4*errors) - 1)
        params, residual, rank, s = solve_leastsq(Amatrix, yval, rcond=-1)
        print(params)
        covMatrix = inv(Amatrix.T * Amatrix)
        vals =  self.a1a2_to_HG(params)
        return vals

    def residuals(self, params, y, x):
        err = y - self.compute_phase_function(x, params)
        return err

    def compute_phase_function(self, beta, params):
        """Computes the Bowell et al. 1989 phase function for phase angle <beta>
        using the H and G parameters.
        """

        phi1 = np.exp(-3.33 * (np.tan(beta/2.0))**0.63)
        phi2 = np.exp(-1.87 * (np.tan(beta/2.0))**1.22)
        mag = params[0] - 2.5 * np.log10((1.0-params[1])*phi1 + params[1]*phi2)

        return mag

    def fit_hg(self, data, degrees=True):
        xval = np.radians(data[:, 0]) if degrees else data[:, 0]
        yval = data[:, 1]

        pname = (['H','G'])
        params0 = np.array([self.H, self.G])
        plsq , pcov, infodict, errmsg, success = leastsq(self.residuals, params0, args=(yval, xval), full_output=True, maxfev=2000)
        # Compute rms of residuals, normalized by no. of degrees of freedom (no.
        # of data points minus no. of model parameters)
        if (len(yval) > len(params0)) and pcov is not None:
            s_sq = (self.residuals(plsq, yval, xval)**2).sum()/(len(yval)-len(plsq))
            pcov = pcov * s_sq
        else:
            pcov = np.inf

        # Use rescaled covariance matrix to estimate errors on paramaters
        error = []
        for i in range(len(plsq)):
            try:
              error.append(np.absolute(pcov[i][i])**0.5)
            except:
              error.append( 0.00 )
        plsq_err = np.array(error)
        #
        # The sum of the residuals
        #
        resid = sum(np.sqrt((self.residuals(plsq, yval, xval))**2))

        return plsq, plsq_err, resid

    def plot_phase_curve(self, measures, colors='r', title='', sub_title=''):
        phases = measures[:, 0]
        mags = measures[:, 1]
        mag_errs = measures[:, 2]

        fig, ax = plt.subplots()
        ax.plot(phases, mags, color=colors, marker='.', linestyle=' ')
        ax.errorbar(phases, mags, yerr=mag_errs, color=colors, linestyle=' ')
        ax.invert_yaxis()
        xmin, xmax = ax.get_xlim()
        ax.set_xlim(0, xmax)
        # Compute and plot phase function
        phase_angles = np.linspace(0, xmax, 100)
        func_mags = self.compute_phase_function(np.radians(phase_angles), (self.H, self.G))
        ax.plot(phase_angles, func_mags, color='k', linestyle='-')
        ax.set_xlabel('Phase angle')
        ax.set_ylabel('Reduced Magnitude')
        fig.suptitle(title)
        ax.set_title(sub_title)
        ax.minorticks_on()
        plt.savefig("phasecurve.png")
        plt.show()

        return

    def handle(self, *args, **options):

        self.stdout.write("==== Phase curve building %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))

        name = options['body']
        self.H = options['H']
        self.G = options['G']
        if name != '44':
            try:
                body = Body.objects.get(Q(provisional_name__exact=name) | Q(provisional_packed__exact=name) | Q(name__exact=name))
            except Body.DoesNotExist:
                self.stdout.write("Body does not exist")
                exit(-1)
            except Body.MultipleObjectsReturned:
                self.stdout.write("Multiple Bodies found")
                exit(-1)

            body_name = body.current_name()
            self.stdout.write("Processing %s" % body_name)
            srcmeas = SourceMeasurement.objects.filter(body=body)
            self.stdout.write("Found %d SourceMeasurements for %s" % (srcmeas.count(), body_name))

            phase_angle_meas = np.zeros((srcmeas.count(), 3))
            for i, src in enumerate(srcmeas):
                phase_angle = body.compute_body_phase_angle(src.frame.midpoint, src.frame.sitecode)
                mag_corr = body.compute_body_mag_correction(src.frame.midpoint, src.frame.sitecode)
                print(phase_angle, mag_corr)
                phase_angle_meas[i, :] = (phase_angle, src.obs_mag-mag_corr, src.err_obs_mag)
        else:
            phase_angle_meas = np.loadtxt("44_Nysa.dat", skiprows=2)

            body_name = '(44) Nysa'

        pfit, perr, residuals = self.fit_hg(phase_angle_meas, degrees=True)
        fit_results = "Results of fit: H={:.2f} (+/- {:.4f}), G={:.2f} (+/- {:.4f})".format(pfit[0], perr[0], pfit[1], perr[1])
        self.stdout.write(fit_results)

        self.H = pfit[0]
        self.G = pfit[1]

        plottitle = "Phase curve for {}".format(body_name)
        self.plot_phase_curve(phase_angle_meas, title=plottitle, sub_title=fit_results)
