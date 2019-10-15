import base64
from datetime import datetime, timedelta
from glob import glob
import io
import logging
import os
import re
import shutil

import aplpy
from django.http import HttpResponse
from django.conf import settings
from django.core.files.storage import default_storage
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from .models import Body, CatalogSources, StaticSource
from astrometrics.ephem_subs import horizons_ephem
from photometrics.obsgeomplot import plot_ra_dec, plot_brightness, plot_helio_geo_dist, \
    plot_uncertainty, plot_hoursup
from photometrics.SA_scatter import readSources, plotScatter, plotFormat
from photometrics.spectraplot import get_spec_plot, make_spec


logger = logging.getLogger(__name__)


def make_visibility_plot(request, pk, plot_type, start_date=datetime.utcnow(), site_code='-1'):

    logger.setLevel(logging.DEBUG)
    try:
        body = Body.objects.get(pk=pk)
    except Body.DoesNotExist:
        return HttpResponse()

    if plot_type not in ['radec', 'mag', 'dist', 'hoursup', 'uncertainty']:
        logger.warning("Invalid plot_type= {}".format(plot_type))
        # Return a 1x1 pixel gif in the case of no visibility file
        PIXEL_GIF_DATA = base64.b64decode(
            b"R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")

        return HttpResponse(PIXEL_GIF_DATA, content_type='image/gif')
    base_dir = os.path.join('visibility', str(body.pk))  # new base_dir for method

    obj = body.name.replace(' ', '').replace('-', '_').replace('+', '')
    site = ''
    if plot_type == 'hoursup' and site_code != '-1':
        site = "_" + site_code + "_"
    # Check if destination exists first. default_storage.listdir() will crash and
    # burn on a non-existant path whereas the prior glob silently returns an
    # empty list
    vis_files = []
    if default_storage.exists(base_dir):
        _, vis_files = default_storage.listdir(path=base_dir)
    if vis_files:
        filematch = "{}.*.{}{}.*.png".format(obj, plot_type, site)
        regex = re.compile(filematch)
        matchfiles = filter(regex.search, vis_files)
        # Find most recent file
        times = [(default_storage.get_modified_time(name=os.path.join(base_dir,i)),os.path.join(base_dir,i)) for i in matchfiles]
        if times:
            _, vis_file = max(times)
        else:
            vis_file = ''
    else:
        vis_file = ''
    if not vis_file:
        start = start_date.date()
        end = start + timedelta(days=31)
        ephem = horizons_ephem(body.name, start, end, site_code)
        if plot_type == 'radec':
            vis_file = plot_ra_dec(ephem)
        elif plot_type == 'mag':
            vis_file = plot_brightness(ephem)
        elif plot_type == 'dist':
            vis_file = plot_helio_geo_dist(ephem)
        elif plot_type == 'uncertainty':
            vis_file = plot_uncertainty(ephem)
        elif plot_type == 'hoursup':
            tel_alt_limit = 30
            to_add_rate = False
            if site_code == '-1':
                site_code = 'W85'
                if ephem['DEC'].mean() > 5:
                    site_code = 'V37'
            if site_code == 'F65' or site_code == 'E10':
                tel_alt_limit = 20
                to_add_rate=True
            ephem = horizons_ephem(body.name, start, end, site_code, '5m', alt_limit=tel_alt_limit)
            vis_file = plot_hoursup(ephem, site_code, add_rate=to_add_rate, alt_limit=tel_alt_limit)
    if vis_file:
        logger.debug('Visibility Plot: {}'.format(vis_file))
        with default_storage.open(vis_file,"rb") as vis_plot:
            return HttpResponse(vis_plot.read(), content_type="Image/png")
    else:
        # Return a 1x1 pixel gif in the case of no visibility file
        PIXEL_GIF_DATA = base64.b64decode(
            b"R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")

        return HttpResponse(PIXEL_GIF_DATA, content_type='image/gif')

def make_plot(request):

    fits_file = 'cpt1m010-kb70-20160428-0148-e91.fits'
    fits_filepath = os.path.join('/tmp', 'tmp_neox_9nahRl', fits_file)

    sources = CatalogSources.objects.filter(frame__filename__contains=fits_file[0:28]).values_list('obs_ra', 'obs_dec')

    fig = aplpy.FITSFigure(fits_filepath)
    fig.show_grayscale(pmin=0.25, pmax=98.0)
    ra = [X[0] for X in sources]
    dec = [X[1] for X in sources]

    fig.show_markers(ra, dec, edgecolor='green', facecolor='none', marker='o', s=15, alpha=0.5)

    buffer = io.BytesIO()
    fig.save(buffer, format='png')
    fig.save(fits_filepath.replace('.fits', '.png'), format='png')

    return HttpResponse(buffer.getvalue(), content_type="Image/png")


def find_spec_plots(path=None, obj=None, req=None, obs_num=None):

    spec_files = None
    if path and obj and obs_num:
        if req:
            if not obs_num.isdigit():
                png_file = "{}/{}_{}_{}".format(path, obj, req, obs_num)
            else:
                png_file = "{}/{}_{}_spectra_{}.png".format(path, obj, req, obs_num)
        else:
            png_file = "{}/{}_spectra_{}.png".format(path, obj, obs_num)
        spec_files = [png_file,]
    return spec_files

def display_calibspec(request, pk):
    try:
        calibsource = StaticSource.objects.get(pk=pk)
    except StaticSource.DoesNotExist:
        logger.debug("Source not found")
        return HttpResponse()

    base_dir = os.path.join('cdbs', 'ctiostan')  # new base_dir for method

    obj = calibsource.name.lower().replace(' ', '').replace('-', '_').replace('+', '')
    obs_num = '1'
    spec_files = find_spec_plots(base_dir, obj, None, obs_num)
    if spec_files:
        spec_file = spec_files[0]
    else:
        spec_file = ''
    if not spec_file:
        spec_file = "f" + obj + ".dat"
        if default_storage.exists(os.path.join(base_dir, spec_file)):
            spec_file = get_spec_plot(base_dir, spec_file, obs_num, log=True)
        else:
            logger.warning("No flux file found for " + spec_file)
            spec_file = ''
    if spec_file and default_storage.exists(spec_file):
        logger.debug('Spectroscopy Plot: {}'.format(spec_file))
        spec_plot = default_storage.open(spec_file, 'rb').read()
        return HttpResponse(spec_plot, content_type="Image/png")
    else:
        logger.debug("No spectrum found for: ", spec_file)
        import base64
        # Return a 1x1 pixel gif in the case of no spectra file
        PIXEL_GIF_DATA = base64.b64decode(
            b"R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")

        return HttpResponse(PIXEL_GIF_DATA, content_type='image/gif')

def make_standards_plot(request):
    """creates stellar standards plot to be added to page"""

    scoords = readSources('Solar')
    fcoords = readSources('Flux')

    ax = plt.figure().gca()
    plotScatter(ax, scoords, 'b*')
    plotScatter(ax, fcoords, 'g*')
    plotFormat(ax, 0)
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    plt.close()

    return HttpResponse(buffer.getvalue(), content_type="Image/png")


def make_solar_standards_plot(request):
    """creates solar standards plot to be added to page"""

    scoords = readSources('Solar')
    ax = plt.figure().gca()
    plotScatter(ax, scoords, 'b*')
    plotFormat(ax, 1)
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    plt.close()

    return HttpResponse(buffer.getvalue(), content_type="Image/png")
