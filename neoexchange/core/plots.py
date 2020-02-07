"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2019-2019 LCO
plots.py -- plotting functions for Neoexchange
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

import base64
from datetime import datetime, timedelta
from glob import glob
import io
import logging
import os
import re
import shutil
import itertools
from math import pi, floor
import numpy as np
from astropy import units as u

import aplpy
from django.http import HttpResponse
from django.conf import settings
from django.core.files.storage import default_storage
import matplotlib
import matplotlib.pyplot as plt

from bokeh.io import curdoc
from bokeh.layouts import layout, column, row
from bokeh.plotting import figure, ColumnDataSource
from bokeh.resources import CDN, INLINE
from bokeh.embed import components, file_html
from bokeh.models import HoverTool, Label, CrosshairTool, Whisker, TeeHead, Range1d, CustomJS
from bokeh.models.widgets import CheckboxGroup, Slider, TableColumn, DataTable, HTMLTemplateFormatter, NumberEditor, NumberFormatter, Spinner, Toggle
from bokeh.palettes import Category20, Category10

from .models import Body, CatalogSources, StaticSource, Block, model_to_dict, PreviousSpectra
from astrometrics.ephem_subs import horizons_ephem, call_compute_ephem, determine_darkness_times, get_sitepos,\
    moon_ra_dec, target_rise_set, moonphase, dark_and_object_up, compute_dark_and_up_time, get_visibility
from photometrics.obsgeomplot import plot_ra_dec, plot_brightness, plot_helio_geo_dist, \
    plot_uncertainty, plot_hoursup
from photometrics.SA_scatter import readSources, plotScatter, plotFormat
from photometrics.spectraplot import spectrum_plot, read_mean_tax

logger = logging.getLogger(__name__)


def find_existing_vis_file(base_dir, filematch):
    """
        Search for the most recent existing visibility file in <base_dir> that
        matches the pattern in <filematch> (should be regex-compilable)
        The filename is returned if matched or a empty string otherwise.
    """

    # Check if destination exists first. default_storage.listdir() will crash and
    # burn on a non-existent path whereas the prior glob silently returns an
    # empty list.
    # Turns out listdir() works on non-existent directories on S3 but not on disk
    # but exists() returns False where or not the "directory" exists or not with
    # S3... So need to do this differently...
    vis_files = []
    try:
        _, vis_files = default_storage.listdir(base_dir)
    except FileNotFoundError:
        pass

    if vis_files:
        regex = re.compile(filematch)
        matchfiles = filter(regex.search, vis_files)
        # Find most recent file
        times = [(default_storage.get_modified_time(name=os.path.join(base_dir, i)), os.path.join(base_dir, i)) for i in matchfiles]
        if times:
            _, vis_file = max(times)
        else:
            vis_file = ''
    else:
        vis_file = ''

    return vis_file


def determine_plot_valid(vis_file, now=datetime.utcnow()):
    """
        Determine if the passed <vis_file> is too old. If it is not too old,
        the filename is returned unmodified, otherwise an empty string is returned.
        The age determination is based on whether the start date (parsed from
        the vis_file filename) is more than 15 days old (for all plot types
        other than 'uncertainty' which uses a 1 day age)
    """

    valid_vis_file = ''
    file_root, ext = os.path.splitext(os.path.basename(vis_file))
    chunks = file_root.split('_')
    if len(chunks) >= 2:
        date_range = chunks[-1]
        plot_type = chunks[-2]
        start_date, end_date = date_range.split('-')
        try:
            start_date_dt = datetime.strptime(start_date, "%Y%m%d")
        except ValueError:
            start_date_dt = datetime.min
        age = now - start_date_dt
        max_age = timedelta(days=15)
        if plot_type == 'uncertainty':
            max_age = timedelta(days=1)
        if age < max_age:
            valid_vis_file = vis_file
        else:
            logger.debug("File '{file}' too old: {start} {now} {age}".format(file=vis_file, start=start_date_dt, now=now, age=age.total_seconds()/86400.0))
    return valid_vis_file


def make_visibility_plot(request, pk, plot_type, start_date=datetime.utcnow(), site_code='-1'):

    try:
        body = Body.objects.get(pk=pk)
    except Body.DoesNotExist:
        return HttpResponse()
    if body.name is None or body.name == '':
        # Body's without a name e.g. NEOCP candidates cannot be looked up in HORIZONS
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
    if plot_type == 'hoursup':
        site = "_" + site_code + "_"
        if site_code == '-1':
            site = "__W85|V37_"
    filematch = "{}.*.{}{}.*.png".format(obj, plot_type, site)
    vis_file = find_existing_vis_file(base_dir, filematch)

    # Determine in existing visibility file is too old
    if vis_file:
        vis_file = determine_plot_valid(vis_file)
    if not vis_file:
        # Check if 'visibility' and per-object subdirectory exists and if not,
        # create the directory. Otherwise this will fail in the plotting routines
        # when doing default_storage.open() using local disk (but won't fail on
        # S3 as directories are not really real there)
        if not default_storage.exists(base_dir):
            try:
                os.makedirs(os.path.join(default_storage.base_location, base_dir))
            except FileExistsError:
                # Race condition exists between os.path.exists() and os.makedirs().
                pass
            except AttributeError:
                # 'PublicMediaStorage' (i.e. S3) doesn't have a `.base_location`...
                pass

        start = start_date.date()
        end = start + timedelta(days=31)
        ephem = horizons_ephem(body.name, start, end, site_code, include_moon=True)
        if ephem:
            if plot_type == 'radec':
                vis_file = plot_ra_dec(ephem, base_dir=base_dir)
            elif plot_type == 'mag':
                vis_file = plot_brightness(ephem, base_dir=base_dir)
            elif plot_type == 'dist':
                vis_file = plot_helio_geo_dist(ephem, base_dir=base_dir)
            elif plot_type == 'uncertainty':
                vis_file = plot_uncertainty(ephem, base_dir=base_dir)
            elif plot_type == 'hoursup':
                tel_alt_limit = 30
                to_add_rate = False
                if site_code == '-1':
                    site_code = 'W85'
                    if ephem['DEC'].mean() > 5:
                        site_code = 'V37'
                if site_code == 'F65' or site_code == 'E10':
                    tel_alt_limit = 20
                    to_add_rate = True
                ephem = horizons_ephem(body.name, start, end, site_code, '5m', alt_limit=tel_alt_limit)
                vis_file = plot_hoursup(ephem, site_code, add_rate=to_add_rate, alt_limit=tel_alt_limit, base_dir=base_dir)
    if vis_file:
        logger.debug('Visibility Plot: {}'.format(vis_file))
        with default_storage.open(vis_file, "rb") as vis_plot:
            return HttpResponse(vis_plot.read(), content_type="Image/png")
    else:
        # Return a 1x1 pixel gif in the case of no visibility file
        PIXEL_GIF_DATA = base64.b64decode(
            b"R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")

        return HttpResponse(PIXEL_GIF_DATA, content_type='image/gif')


# def make_plot(request):
#
#     fits_file = 'cpt1m010-kb70-20160428-0148-e91.fits'
#     fits_filepath = os.path.join('/tmp', 'tmp_neox_9nahRl', fits_file)
#
#     sources = CatalogSources.objects.filter(frame__filename__contains=fits_file[0:28]).values_list('obs_ra', 'obs_dec')
#
#     fig = aplpy.FITSFigure(fits_filepath)
#     fig.show_grayscale(pmin=0.25, pmax=98.0)
#     ra = [X[0] for X in sources]
#     dec = [X[1] for X in sources]
#
#     fig.show_markers(ra, dec, edgecolor='green', facecolor='none', marker='o', s=15, alpha=0.5)
#
#     buffer = io.BytesIO()
#     fig.save(buffer, format='png')
#     fig.save(fits_filepath.replace('.fits', '.png'), format='png')
#
#     return HttpResponse(buffer.getvalue(), content_type="Image/png")

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


def spec_plot(data_spec, analog_data, reflec=False):
    """Builds the actual Bokeh Plots for various spectra
        INPUTS:
            data_spec: Array of dictionaries containing 'wav', 'spec', 'err', 'label', and 'filename'
            analog_data: single data_spec like dictionary containing Solar Analog Spectrum
            reflec: Flag determinine if the data_spec data has already had the solar spectrum removed.
    """

    spec_plots = {}
    if not reflec and data_spec[0]:
        if data_spec[0]["spec"].unit == u.dimensionless_unscaled:
            plot = figure(x_range=(3500, 10500), y_range=(0, 1.75), plot_width=800, plot_height=400)
            plot.yaxis.axis_label = 'Relative Spectra (Normalized at 5500 Å)'
        else:
            plot = figure( plot_width=600, plot_height=400)
            plot.yaxis.axis_label = 'Flux ({})'.format(data_spec[0]["spec"].unit)
        for spec in data_spec:
            plot.line(spec['wav'], spec['spec'], legend_label=spec['label'], muted_alpha=0.25)
        plot.legend.click_policy = 'mute'

        # Set Axes
        plot.axis.axis_line_width = 2
        plot.axis.axis_label_text_font_size = "12pt"
        plot.axis.major_tick_line_width = 2
        plot.xaxis.axis_label = "Wavelength (Å)"
        spec_plots["raw_spec"] = plot

    if reflec or (data_spec[0] and analog_data and data_spec[0]['label'] != analog_data[0]['label']):
        if not reflec:
            first = True
            for analog in analog_data:
                if first:
                    muted_alpha = 0.25
                    first = False
                else:
                    muted_alpha = 0
                plot.line(analog['wav'], analog['spec'], color="firebrick", legend_label=analog['label'], muted=True, muted_alpha=muted_alpha, muted_color="firebrick")
        # Build Reflectance Plot
        plot2 = figure(x_range=(3500, 10500), y_range=(0.5, 1.75), plot_width=800, plot_height=400)
        spec_dict = read_mean_tax()
        spec_dict["Wavelength"] = [l*10000 for l in spec_dict["Wavelength"]]

        stand_list = ['A', 'B', 'C', 'D', 'L', 'Q', 'S', 'Sq', 'V', 'X', 'Xe']
        init_stand = ['C', 'Q', 'S', 'X']
        colors = Category20[len(stand_list)]
        for j, tax in enumerate(stand_list):
            lower = np.array([mean - spec_dict[tax + '_Sigma'][i] for i, mean in enumerate(spec_dict[tax + "_Mean"])])
            upper = np.array([mean + spec_dict[tax + '_Sigma'][i] for i, mean in enumerate(spec_dict[tax + "_Mean"])])
            wav_box = np.array(spec_dict["Wavelength"])
            xs = np.concatenate([wav_box, wav_box[::-1]])
            ys = np.concatenate([upper, lower[::-1]])

            if tax in init_stand:
                vis = True
            else:
                vis = False

            source = ColumnDataSource(spec_dict)

            plot2.line("Wavelength", tax+"_Mean", source=source, color=colors[j], name=tax + "-Type", line_width=2, line_dash='dashed', legend_label=tax, visible=vis)
            plot2.patch(xs, ys, fill_alpha=.25, line_width=1, fill_color=colors[j], line_color="black", name=tax + "-Type", legend_label=tax, line_alpha=.25, visible=vis)

        if not reflec:
            for spec in data_spec:
                data_label_reflec, reflec_spec, reflec_ast_wav = spectrum_plot(spec['filename'], analog=analog_data[0]['filename'])
                plot2.line(reflec_ast_wav, reflec_spec, line_width=3, name=spec['label'])
                plot2.title.text = 'Object: {}    Analog: {}'.format(spec['label'], analog_data[0]['label'])
        else:
            for spec in data_spec:
                plot2.circle(spec['wav'], spec['spec'], size=3, name=spec['label'])
            title = data_spec[0]['label']
            for d in data_spec:
                if d['label'] != title:
                    chunks = d['label'].split("--")
                    title += ' /' + chunks[1]
            plot2.title.text = 'Object: {}'.format(title)

        hover = HoverTool(tooltips="$name", point_policy="follow_mouse", line_policy="none")

        plot2.add_tools(hover)
        plot2.legend.click_policy = 'hide'
        plot2.legend.orientation = 'horizontal'

        # set axes
        plot2.axis.axis_line_width = 2
        plot2.axis.axis_label_text_font_size = "12pt"
        plot2.axis.major_tick_line_width = 2
        plot2.xaxis.axis_label = "Wavelength (Å)"
        plot2.yaxis.axis_label = 'Reflectance Spectra (Normalized at 5500 Å)'

        spec_plots["reflec_spec"] = plot2

    # Create script/div
    if spec_plots:
        script, div = components(spec_plots, CDN)
    else:
        return '', {"raw_spec": ''}
    try:
        for key in div.keys():
            b = div[key].index('>')
            div[key] = '{} name={}{}'.format(div[key][:b], key, div[key][b:])
    except ValueError:
        pass
    return script, div


def datetime_to_radians(ref_time, input_time):
    """Function to convert the difference between two times into a difference in radians relative to a 24 hour clock."""

    if input_time:
        t_diff = input_time - ref_time
        t_diff_hours = t_diff.total_seconds()/3600
        t_diff_radians = t_diff_hours/24*2*pi + pi/2
    else:
        t_diff_radians = 0
    return t_diff_radians


def build_visibility_source(body, site_list, site_code, color_list, d, alt_limit, step_size):
    """Builds the source dictionaries used by lin_vis_plot"""

    body_elements = model_to_dict(body)
    mag = None
    vis = {"x": [],
           "y": [],
           "sun_rise": [],
           "sun_set": [],
           "obj_rise": [],
           "obj_set": [],
           "moon_rise": [],
           "moon_set": [],
           "moon_phase": [],
           "colors": [],
           "line_alpha": [],
           "site": [],
           "obj_vis": [],
           "max_alt": []
           }

    for i, site in enumerate(site_list):
        bonus_day = 0
        dark_start, dark_end = determine_darkness_times(site, d)
        while dark_start < d:
            bonus_day += 1
            dark_start, dark_end = determine_darkness_times(site, d + timedelta(days=bonus_day))
        (site_name, site_long, site_lat, site_hgt) = get_sitepos(site)
        (moon_app_ra, moon_app_dec, diam) = moon_ra_dec(d, site_long, site_lat, site_hgt)
        moon_rise, moon_set, moon_max_alt, moon_vis_time = target_rise_set(d, moon_app_ra, moon_app_dec, site, 10, step_size, sun=False)
        moon_phase = moonphase(d, site_long, site_lat, site_hgt)
        emp = call_compute_ephem(body_elements, d, d + timedelta(days=1), site, step_size, perturb=False)
        obj_up_emp = dark_and_object_up(emp, d, d + timedelta(days=1), 0 , alt_limit=alt_limit)
        vis_time, emp_obj_up, set_time = compute_dark_and_up_time(obj_up_emp, step_size)
        obj_set = datetime_to_radians(d, set_time)
        dark_and_up_time, max_alt = get_visibility(None, None, d + timedelta(days=bonus_day), site, step_size, alt_limit, False, body_elements)
        vis["x"].append(0)
        vis["y"].append(0)
        vis["sun_rise"].append(datetime_to_radians(d, dark_end))
        vis["sun_set"].append(datetime_to_radians(d, dark_start))
        vis["obj_rise"].append(obj_set-(vis_time/24*2*pi))
        vis["obj_set"].append(obj_set)
        vis["moon_rise"].append(datetime_to_radians(d, moon_set)-(moon_vis_time/24*2*pi))
        vis["moon_set"].append(datetime_to_radians(d, moon_set))
        vis["moon_phase"].append(moon_phase)
        vis["colors"].append(color_list[i])
        if vis_time > 0:
            vis["line_alpha"].append(1)
        else:
            vis["line_alpha"].append(0)
        vis["site"].append(site_code[i])
        vis["obj_vis"].append(dark_and_up_time)
        vis["max_alt"].append(max_alt)
        if emp:
            mag = emp[0][3]

    return vis, mag


def lin_vis_plot(body):
    """Creates a Bokeh plot showing the visibility for the given body over the next 24 hours compared to the
        current time, the sun and the moon. Contains a help overview for first time viewers.
    """

    site_code = ['LSC', 'CPT', 'COJ', 'ELP', 'TFN', 'OGG']
    site_list = ['W85', 'K91', 'Q63', 'V37', 'Z21', 'F65']
    color_list = ['darkviolet', 'forestgreen', 'saddlebrown', 'coral', 'darkslategray', 'dodgerblue']
    d = datetime.utcnow()
    step_size = '30 m'
    alt_limit = 30

    vis, mag = build_visibility_source(body, site_list, site_code, color_list, d, alt_limit, step_size)
    new_x = []
    for i, l in enumerate(site_code):
        new_x.append(-1 + i * ( 2 / (len(site_list)-1)))
    vis['x'] = new_x
    rad = ((2 / (len(site_list)-1))*.9)/2

    source = ColumnDataSource(data=vis)

    TOOLTIPS = """
            <div>
                <div>
                    <span style="font-size: 17px; font-weight: bold; color: @colors;">@site</span>
                </div>
                <div>
                    <span style="font-size: 15px;">Visibility:</span>
                    <span style="font-size: 10px; color: #696;">@obj_vis{1.1} hours</span>
                    <br>
                    <span style="font-size: 15px;">Max Alt:</span>
                    <span style="font-size: 10px; color: #696;">@max_alt deg</span>
                    """

    # Add vmag
    if mag:
        TOOLTIPS += """
                    <br>
                    <span style="font-size: 15px;">V Mag:</span>
                    <span style="font-size: 10px; color: #696;">{}</span>
                </div>
            </div>
        """.format(mag)

    hover = HoverTool(tooltips=TOOLTIPS, point_policy="none", attachment='below', line_policy="none")
    plot = figure(toolbar_location=None, x_range=(-1.5, 1.5), y_range=(-.5, .5), tools=[hover], plot_width=300,
                  plot_height=75)
    plot.grid.visible = False
    plot.outline_line_color = None
    plot.axis.visible = False

    # base
    plot.circle(x='x', y='y', radius=rad, fill_color="white", source=source, line_color="black", line_width=2)
    # object
    plot.wedge(x='x', y='y', radius=rad, start_angle="obj_rise", end_angle="obj_set", color="colors", line_color="black",line_alpha="line_alpha", source=source)
    # sun
    plot.wedge(x='x', y='y', radius=rad * .75, start_angle="sun_rise", end_angle="sun_set", color="khaki", line_color="black", source=source)
    # moon
    plot.wedge(x='x', y='y', radius=rad * .5, start_angle="moon_rise", end_angle="moon_set", color="gray", line_color="black",
               fill_alpha='moon_phase', source=source)

    # Build Clock
    plot.ray('x', 'y', angle=pi/2, length=rad, color="red", alpha=.75, line_width=2, source=source)
    plot.ray('x', 'y', angle=0, length=rad, color="gray", alpha=.75, source=source)
    plot.ray('x', 'y', angle=pi, length=rad, color="gray", alpha=.75, source=source)
    plot.ray('x', 'y', angle=3*pi/2, length=rad, color="gray", alpha=.75, source=source)
    plot.circle('x', 'y', radius=rad * .25, fill_color="white", line_width=1, line_color="black", source=source)

    # Build Help
    # plot Base
    plot.circle(x='x', y='y', radius=rad, color="white", source=source, alpha=0.75, legend_label="?", visible=False)

    # Plot target help
    up_index_list = [i for i, x in enumerate(vis['x']) if vis["obj_rise"][i] != 0 and vis["obj_set"][i] != 0]
    if 1 in up_index_list or not up_index_list:
        up_index = 1
    elif len(up_index_list) > 1 and not up_index_list[0]:
        up_index = up_index_list[1]
    else:
        up_index = up_index_list[0]

    plot.wedge(x=vis['x'][up_index], y=vis['y'][up_index], radius=rad, start_angle=vis["obj_rise"][up_index], end_angle=vis["obj_set"][up_index], fill_color=vis["colors"][up_index], line_color="black", legend_label="?", visible=False)

    plot.text(vis['x'][up_index], [rad + .1], text=["Target"], text_color=vis["colors"][up_index], text_align='center', text_font_size='10px', legend_label="?", visible=False)
    n = list(range(len(site_list)))
    n.remove(up_index)

    # Plot Now help
    plot.text([vis['x'][n[0]]], [rad+.1], text=["Now"], text_color='red', text_align='center', text_font_size='10px', legend_label="?", visible=False)
    plot.ray([vis['x'][n[0]]], [0], angle=pi/2, length=rad, color="red", alpha=.75, line_width=2, legend_label="?", visible=False)

    # Plot sun help
    plot.wedge(x=vis['x'][n[1]], y=vis['y'][n[1]], radius=rad * .75, start_angle=vis["sun_rise"][n[1]], end_angle=vis["sun_set"][n[1]], fill_color="khaki", line_color="black", legend_label="?", visible=False)
    plot.text(vis['x'][n[1]], [rad+.1], text=["Sun"], text_color="darkgoldenrod", text_align='center', text_font_size='10px', legend_label="?", visible=False)

    # Plot moon help
    plot.wedge(x=vis['x'][n[2]], y=vis['y'][n[2]], radius=rad * .5, start_angle=vis["moon_rise"][n[2]], end_angle=vis["moon_set"][n[2]], fill_color="gray", line_color="black", fill_alpha=vis['moon_phase'][n[2]], legend_label="?", visible=False)
    plot.text(vis['x'][n[2]], [rad + .1], text=["Moon"], text_color="dimgray", text_align='center', text_font_size='10px', legend_label="?", visible=False)

    # plot time direction
    plot.arc(vis['x'][n[3]], vis['y'][n[3]], radius=rad * .6, start_angle=0, end_angle=pi, color="black", line_width=2, direction='clock', legend_label="?", visible=False)
    plot.triangle(vis['x'][n[3]]-(rad * .58), vis['y'][n[3]], color="black", size=6, legend_label="?", visible=False)
    plot.text(vis['x'][n[3]], [rad+.1], text=["Time"], text_color='black', text_align='center', text_font_size='10px', legend_label="?", visible=False)

    # plot hours help
    plot.ray(vis['x'][n[4]], [0], angle=0, length=rad, color="black", legend_label="?", visible=False)
    plot.ray(vis['x'][n[4]], [0], angle=pi, length=rad, color="black", legend_label="?", visible=False)
    plot.ray(vis['x'][n[4]], [0], angle=3*pi/2, length=rad, color="black", legend_label="?", visible=False)
    plot.text(vis['x'][n[4]], [rad+.1], text=["6 hours"], text_color='black', text_align='center', text_font_size='10px', legend_label="?", visible=False)

    # plot center help
    plot.circle('x', 'y', radius=rad * .25, fill_color="white", line_width=1, line_color="black", source=source, legend_label="?", visible=False)

    # plot site labels
    plot.line([vis['x'][0]-rad, vis['x'][0]-rad, vis['x'][0]], [-rad - .1, -rad - .22, -rad - .22], color="navy", legend_label="?", visible=False)
    plot.line([vis['x'][2], vis['x'][2]+rad, vis['x'][2]+rad], [-rad - .22, -rad - .22, -rad - .1], color="navy", legend_label="?", visible=False)
    plot.text(vis['x'][1], [-rad-.3], text=["Southern Sites"], text_color='navy', text_align='center', text_font_size='10px', legend_label="?", visible=False)
    plot.line([vis['x'][3]-rad, vis['x'][3]-rad, vis['x'][3]], [-rad - .1, -rad - .22, -rad - .22], color="maroon", legend_label="?", visible=False)
    plot.line([vis['x'][5], vis['x'][5]+rad, vis['x'][5]+rad], [-rad - .22, -rad - .22, -rad - .1], color="maroon", legend_label="?", visible=False)
    plot.text(vis['x'][4], [-rad-.3], text=["Northern Sites"], text_color='maroon', text_align='center', text_font_size='10px', legend_label="?", visible=False)

    # Build over layer for smooth tooltips
    plot.circle(x='x', y='y', radius=rad, color="white", source=source, alpha=0.01, legend_label="?", visible=False)

    plot.legend.click_policy = 'hide'
    plot.legend.background_fill_alpha = 0
    plot.legend.border_line_alpha = 0
    plot.legend.margin = 0
    plot.legend.glyph_width = 0
    plot.legend.glyph_height = 0
    plot.legend.label_width = 0
    plot.legend.label_height = 0

    script, div = components(plot, CDN)

    return script, div


def get_name(meta_dat):
    name = meta_dat['OBJECTNAME']
    number = meta_dat['OBJECTNUMBER']
    desig = meta_dat['MPCDESIG']
    if name != 'False' and (number != 'False' and number != '0'):
        out_string = '{} ({})'.format(name, number)
    elif name != 'False':
        out_string = '{}'.format(name)
    elif number != 'False' and desig != 'False' and number != '0':
        out_string = '{} ({})'.format(number, desig)
    elif number != 'False' and number != '0':
        out_string = '{}'.format(number)
    elif desig != 'False':
        out_string = '{}'.format(desig)
    else:
        out_string = 'UNKNOWN OBJECT'
    return out_string, name, number


def lc_plot(lc_list, meta_list, filt_list, period=None):

    plot = figure(plot_width=900, plot_height=400)
    plot.y_range.flipped = True

    # Create Column Data Source that will be used by the plot
    source = ColumnDataSource(data=dict(time=[], mag=[], color=[], title=[], err_high=[], err_low=[], alpha=[]))
    orig_source = ColumnDataSource(data=dict(time=[], mag=[], mag_err=[], color=[], title=[], err_high=[], err_low=[], alpha=[]))
    dataset_source = ColumnDataSource(data=dict(symbol=[], date=[], time=[], site=[], filter=[], color=[], title=[], offset=[]))

    # Create Input controls
    phase_shift = Slider(title="Phase Offset", value=0, start=-1, end=1, step=.01)
    if period:
        default_period = period
    else:
        default_period = 1.0
    max_period = 10 * default_period
    min_period = 0.0
    step = (max_period - min_period)/1000
    period_slider = Slider(title=None, value=default_period, start=min_period, end=max_period, step=step)
    period_box = Spinner(value=default_period, low=0, step=step, title="Period", width=200)
    p_slider_min = Spinner(value=min_period, low=0, step=.01, title="min", width=100)
    p_slider_max = Spinner(value=max_period, low=0, step=.01, title="max", width=100)
    phase_toggle = Toggle(label="Phase", button_type="primary", width=100, align='end')

    # Create plot
    error_cap = TeeHead(line_alpha=0)
    plot.add_layout(
        Whisker(source=source, base="time", upper="err_high", lower="err_low", line_color="color", line_alpha="alpha",
                lower_head=error_cap, upper_head=error_cap))
    plot.circle(x="time", y="mag", source=source, size=3, color="color", alpha="alpha")

    filt_unique = list(set(filt_list))
    filt_sets = {}
    for filt_u in filt_unique:
        filt_sets[filt_u] = []
        for i, filt in enumerate(filt_list):
            if filt == filt_u:
                filt_sets[filt_u].append(i)

    obj, name, num = get_name(meta_list[0])
    date_range = meta_list[0]['SESSIONDATE'].replace('-', '')+'-'+meta_list[-1]['SESSIONDATE'].replace('-', '')
    base_date = floor(min(sorted([jd for lc in lc_list for jd in lc['date']])))
    colors = itertools.cycle(Category10[10])
    plot.yaxis.axis_label = 'Apparent Magnitude'
    plot.title.text = 'LC for {} ({})'.format(obj, date_range)

    def update():
        x_times = []
        y_mags = []
        mag_err = []
        hi_errs = []
        low_errs = []
        dat_colors = []
        dat_alphas = []
        data_title = []
        sess_date = []
        sess_time = []
        sess_filt = []
        sess_site = []
        sess_title = []
        sess_color = []
        phased_lc_list = phase_lc(lc_list, period, base_date)
        if period:
            for lc in phased_lc_list:
                for k, phase in enumerate(lc['date']):
                    if 0 < phase < 0.5:
                        lc['date'].append(phase+1)
                        lc['mags'].append(lc['mags'][k])
                        lc['mag_errs'].append(lc['mag_errs'][k])
                    elif 0.5 < phase < 1:
                        lc['date'].append(phase-1)
                        lc['mags'].append(lc['mags'][k])
                        lc['mag_errs'].append(lc['mag_errs'][k])

        for c, lc in enumerate(phased_lc_list):
            plot_col = next(colors)
            # Build Error Bars
            err_up = np.array(lc['mags']) + np.array(lc['mag_errs'])
            err_low = np.array(lc['mags']) - np.array(lc['mag_errs'])

            # build source data
            x_times += lc['date']
            y_mags += lc['mags']
            mag_err += lc['mag_errs']
            hi_errs += list(err_up)
            low_errs += list(err_low)
            dat_colors += [plot_col]*len(lc['date'])
            dat_alphas += [1]*len(lc['date'])

            # Build dataset_title
            md = meta_list[c]
            sess_date.append(md['SESSIONDATE'])
            sess_time.append(md['SESSIONTIME'])
            sess_filt.append(md['FILTER'])
            sess_site.append(md['MPCCODE'])
            sess_color.append(plot_col)
            dataset_title = "{}T{} -- Filter:{} -- Site:{}".format(md['SESSIONDATE'], md['SESSIONTIME'], md['FILTER'], md['MPCCODE'])
            sess_title.append(dataset_title)
            data_title += [dataset_title]*len(lc['date'])
        sess_sym = ['&#10739;']*len(sess_date)
        offset = [0]*len(sess_date)
        dataset_source.data = dict(symbol=sess_sym, date=sess_date, time=sess_time, site=sess_site, filter=sess_filt, color=sess_color, title=sess_title, offset=offset)
        source.data = dict(time=x_times, mag=y_mags, color=dat_colors, title=data_title, err_high=hi_errs, err_low=low_errs, alpha=dat_alphas)
        orig_source.data = dict(time=x_times, mag=y_mags, color=dat_colors, title=data_title, err_high=hi_errs, err_low=low_errs, alpha=dat_alphas, mag_err=mag_err)

    update()  # initial load of the data

    template = """
                <p style="color:<%=
                    (function colorfromint(){
                        return(color)
                    }()) %>;">
                    <%= value %>
                </p>
                """
    formatter = HTMLTemplateFormatter(template=template)

    columns = [
        TableColumn(field="symbol", title='', formatter=formatter, width=3),
        TableColumn(field="date", title="Date"),
        TableColumn(field="time", title="Time"),
        TableColumn(field="site", title="Site"),
        TableColumn(field="filter", title="Filter"),
        TableColumn(field="offset", title="Mag Offset", editor=NumberEditor(step=.1), formatter=NumberFormatter(format="0.0"))
    ]

    dataset_source.selected.indices = list(range(len(dataset_source.data['date'])))
    data_table = DataTable(source=dataset_source, columns=columns, width=600, height=300, selectable='checkbox', index_position=None, editable=True)

    callback = CustomJS(args=dict(source=source, phase_shift=phase_shift, period=period, dataset_source=dataset_source, osource=orig_source),
                        code="""const data = source.data;
                                const base = osource.data;
                                const B = phase_shift.value;
                                const I = dataset_source.selected.indices;
                                const T = dataset_source.data['title'];
                                const O = dataset_source.data['offset'];
                                const x = data['time'];
                                const y = data['mag'];
                                const el = data['err_low'];
                                const eh = data['err_high'];
                                const d = base['time'];
                                const m = base['mag'];
                                const me = base['mag_err'];
                                const t = data['title'];
                                const a = data['alpha'];
                                var selected = [];
                                var offy = [];
                                for (var i = 0; i < I.length; i++) {
                                    selected[i] = T[I[i]];
                                    if (O[I[i]] != 0) {
                                        offy.push(I[i]);
                                    }
                                }
                                for (var i = 0; i < x.length; i++) {
                                    if (period > 0){
                                        x[i] = d[i] + B;
                                        if (x[i] > 1.5){
                                            x[i] = x[i] - 2.0;
                                        }
                                        if (x[i] < -.5){
                                            x[i] = x[i] + 2.0;
                                        }
                                    }
                                    if (selected.includes(t[i])){
                                        a[i] = 1;
                                    } else {
                                        a[i] = 0;
                                    }
                                    if (offy != []) {
                                        for (var k = 0; k < offy.length; k++) {
                                            if (t[i] == T[offy[k]]) {
                                                y[i] = m[i] + O[offy[k]];
                                                el[i] = m[i] - me[i] + O[offy[k]];
                                                eh[i] = m[i] + me[i] + O[offy[k]];
                                                k = offy.length
                                            } else {
                                                y[i] = m[i];
                                                el[i] = m[i] - me[i];
                                                eh[i] = m[i] + me[i];
                                            }
                                        }
                                    } else {
                                        y[i] = m[i]
                                        el[i] = m[i] - me[i];
                                        eh[i] = m[i] + me[i];
                                    }
                                }
                                source.change.emit();
                                """)

    phase_shift.js_on_change('value', callback)
    dataset_source.selected.js_on_change('indices', callback)

    period_bounds_callback = CustomJS(args=dict(period_box=period_box, period_slider=period_slider, p_max=p_slider_max, p_min=p_slider_min),
                        code="""
                        if (p_min.value < 0){
                            p_min.value = 0;
                        }
                        if (p_max.value <= p_min.value){
                            p_max.value = p_min.value + 1;
                        }
                        period_slider.end = p_max.value;
                        period_slider.start = p_min.value;
                        if (period_slider.value < p_min.value){
                            period_slider.value = p_min.value;
                        }
                        if (period_slider.value > p_max.value){
                            period_slider.value = p_max.value;
                        }
                        period_slider.step = ((p_max.value - p_min.value) / 1000 );
                        period_box.step = ((p_max.value - p_min.value) / 1000 );
                        """)
    p_slider_max.js_on_change('value', period_bounds_callback)
    p_slider_min.js_on_change('value', period_bounds_callback)

    period_slider.js_link('value', period_box, 'value')

    if period:
        plot.xaxis.axis_label = 'Phase (Period = {}h)'.format(period)
        plot.x_range = Range1d(0, 1.1, bounds=(-.2, 1.2))
    else:
        plot.xaxis.axis_label = 'Date (Hours from {}.0)'.format(base_date)
    phased_callback = CustomJS(args=dict(phase_toggle=phase_toggle, source=source, period_box=period_box, period_slider=period_slider, plot=plot, osource=orig_source, x_axis=plot.xaxis),
                        code="""
                        if (period_box.value <= 0){
                            period_box.value = 0;
                        }
                        const data = source.data;
                        const base = osource.data;
                        const x = data['time'];
                        const d = base['time'];
                        const y = data['mag'];
                        const m = base['mag'];
                        const el = data['err_low'];
                        const eh = data['err_high'];
                        const me = base['mag_err'];
                        const t = data['title'];
                        const a = data['alpha'];
                        const c = data['color'];
                        const period = period_box.value;
                        period_slider.value = period_box.value;
                        let pos = d.length - 1;
                        let n = x.length - d.length;
                        x.splice(pos,n);
                        y.splice(pos,n);
                        el.splice(pos,n);
                        eh.splice(pos,n);
                        a.splice(pos,n);
                        t.splice(pos,n);
                        c.splice(pos,n);
                        if ((period > 0) && (phase_toggle.active)) {
                            for (var i = 0; i < d.length; i++){
                                x[i] = (d[i] / period);
                                x[i] = x[i] - Math.floor(x[i]);
                                if ((x[i] > 0.0) && (x[i] < 0.5)){
                                    x.push(x[i] + 1.0);
                                } else if ((x[i] < 1.0) && (x[i] > 0.5)){
                                    x.push(x[i] - 1.0);
                                }
                                y.push(y[i]);
                                el.push(el[i]);
                                eh.push(eh[i]);
                                a.push(a[i]);
                                t.push(t[i]);
                                c.push(c[i]);
                            }
                            x_axis.axis_label = 'Phase (Period = ' + String(period) + 'h)';
                        } else{
                            for (var i = 0; i < d.length; i++){
                                if (i <= (d.length - 1)){
                                    x[i] = d[i];
                                }
                            }
                        x_axis.axis_label = 'Date (Hours from Basedate)';
                        }
                        if (phase_toggle.active){
                            phase_toggle.label = 'Un-Phase';
                        } else {
                            phase_toggle.label = 'Phase';
                        }
                        source.change.emit();
                        plot.x_range['start'] = 0;
                        plot.x_range['end'] = 1.2;
                        console.log(plot.x_range.min);
                        console.log(plot.x_range.start);
                        console.log(plot.x_range.max);
                        console.log(plot.x_range.end);
                        console.log(plot.x_range);
                        """)
    phase_toggle.js_on_click(phased_callback)
    period_box.js_on_change('value', phased_callback)

    period_layout = row( column( row(phase_toggle, period_box), period_slider, phase_shift), column(p_slider_min, p_slider_max))

    script, div = components({'plot': plot, 'table': data_table, 'period': period_layout}, CDN)

    return script, div


def phase_lc(lc_data, period, base_date):
    """Remove base JD, convert to hours, and fold LC around period.
        If Period=None, Just remove Base JD and convert to Hours.
    """
    phase_list = []
    for lc in lc_data:
        if period:
            phase = [(x - base_date) * 24 / period for x in lc['date']]
            phase = [x - x // 1 for x in phase]
        else:
            phase = [(x - base_date) * 24 for x in lc['date']]
        lc['date'] = phase
        phase_list.append(lc)
    return phase_list
