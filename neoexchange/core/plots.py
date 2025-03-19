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
import copy
from datetime import datetime, timedelta
from glob import glob
import io
import logging
import os
import re
import shutil
import itertools
from math import pi, floor, radians, degrees
import numpy as np
from astropy import units as u

from django.http import HttpResponse
from django.conf import settings
from django.core.files.storage import default_storage
import matplotlib
import matplotlib.pyplot as plt

from bokeh.io import curdoc
from bokeh.layouts import layout, column, row
from bokeh.plotting import figure
from bokeh.resources import CDN, INLINE
from bokeh.embed import components, file_html
from bokeh.models import HoverTool, LabelSet, CrosshairTool, Whisker, TeeHead, Range1d, CustomJS, Title, CustomJSHover,\
    DataRange1d, Tool, ColumnDataSource, LinearAxis
from bokeh.models.widgets import CheckboxGroup, Slider, TableColumn, DataTable, HTMLTemplateFormatter, NumberEditor,\
    NumberFormatter, Spinner, Button, Panel, Tabs, Div, Toggle, Select, MultiSelect
from bokeh.palettes import Category20, Category10
from bokeh.colors import HSL
from bokeh.core.properties import Instance, String, List
from bokeh.util.compiler import TypeScript

from .models import Body, CatalogSources, StaticSource, Block, model_to_dict, PreviousSpectra
from astrometrics.ephem_subs import horizons_ephem, call_compute_ephem, determine_darkness_times, get_sitepos,\
    moon_ra_dec, target_rise_set, moonphase, dark_and_object_up, compute_dark_and_up_time, get_visibility,\
    compute_ephem, orbital_pos_from_true_anomaly, get_planetary_elements
from astrometrics.time_subs import jd_utc2datetime
from photometrics.obsgeomplot import plot_ra_dec, plot_brightness, plot_helio_geo_dist, \
    plot_uncertainty, plot_hoursup, plot_gal_long_lat
from photometrics.catalog_subs import sanitize_object_name
from photometrics.SA_scatter import readSources, plotScatter, plotFormat
from photometrics.spectraplot import spectrum_plot, read_mean_tax
import os
from datetime import datetime, timedelta

from astrometrics import *
from astrometrics.ephem_subs import horizons_ephem
from core.models import SuperBlock, Block, Frame, StaticSource, User
import core as core

import numpy as np
import matplotlib
#matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import AutoMinorLocator
from operator import itemgetter
from importlib import reload
plt=reload(plt)

logger = logging.getLogger(__name__)

# JS file containing call back functions
js_file = os.path.abspath(os.path.join('core', 'static', 'core', 'js', 'bokeh_custom_javascript.js'))


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


def determine_plot_valid(vis_file, now=None):
    """
        Determine if the passed <vis_file> is too old. If it is not too old,
        the filename is returned unmodified, otherwise an empty string is returned.
        The age determination is based on whether the start date (parsed from
        the vis_file filename) is more than 15 days old (for all plot types
        other than 'uncertainty' which uses a 1 day age)
    """

    now = now or datetime.utcnow()

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
            logger.debug("File '{file}' too old: {start} {now} {age}".format(file=vis_file, start=start_date_dt,
                                                                             now=now, age=age.total_seconds()/86400.0))
    return valid_vis_file


def make_visibility_plot(request, pk, plot_type, start_date=None, site_code='-1'):

    try:
        body = Body.objects.get(pk=pk)
    except Body.DoesNotExist:
        return HttpResponse()
    if body.name is None or body.name == '':
        # Body's without a name e.g. NEOCP candidates cannot be looked up in HORIZONS
        return HttpResponse()

    if plot_type not in ['radec', 'mag', 'dist', 'hoursup', 'uncertainty', 'glonglat']:
        logger.warning("Invalid plot_type= {}".format(plot_type))
        # Return a 1x1 pixel gif in the case of no visibility file
        PIXEL_GIF_DATA = base64.b64decode(
            b"R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")

        return HttpResponse(PIXEL_GIF_DATA, content_type='image/gif')

    start_date = start_date or datetime.utcnow()
    base_dir = os.path.join('visibility', str(body.pk))  # new base_dir for method
    obj = sanitize_object_name(body.name)
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
            elif plot_type == 'glonglat':
                vis_file = plot_gal_long_lat(ephem, base_dir=base_dir)
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
            return HttpResponse(vis_plot.read(), content_type="image/png")
    else:
        # Return a 1x1 pixel gif in the case of no visibility file
        logger.debug('No visibility plot')
        PIXEL_GIF_DATA = base64.b64decode(
            b"R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")

        return HttpResponse(PIXEL_GIF_DATA, content_type='image/gif')


# def make_plot(request):
#     import aplpy
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

    if reflec:
        spec_type = 'reflect_only'
    elif data_spec[0] and analog_data and data_spec[0]['label'] != analog_data[0]['label']:
        spec_type = 'raw_and_reflect'
    else:
        spec_type = 'raw_only'

    # build plots
    raw_plot = figure(plot_width=800, plot_height=400)
    ref_plot = figure(x_range=(3500, 10500), y_range=(0.5, 1.75), plot_width=800, plot_height=400)
    raw_lines = []
    if 'raw' in spec_type:
        if data_spec[0]["spec"].unit == u.dimensionless_unscaled:
            raw_plot = figure(plot_width=800, plot_height=400, x_range=(3500, 10500), y_range=(0, 1.75))
            raw_plot.yaxis.axis_label = 'Relative Spectra (Normalized at 5500 Å)'
        else:
            raw_plot.plot_width = 600
            raw_plot.yaxis.axis_label = 'Flux ({})'.format(data_spec[0]["spec"].unit)
            spec_type = "raw_standard"
        for spec in data_spec:
            raw_lines.append(raw_plot.line(spec['wav'], spec['spec'], muted_alpha=0.25))

        # Set Axes
        raw_plot.axis.axis_line_width = 2
        raw_plot.axis.axis_label_text_font_size = "12pt"
        raw_plot.axis.major_tick_line_width = 2
        raw_plot.xaxis.axis_label = "Wavelength (Å)"

    reflect_source_prefs = []
    reflect_source_lists = []
    reflectance_lines = []
    analog_sources_raw = []
    for analog in analog_data:
        analog_sources_raw.append(ColumnDataSource(data=dict(wav=analog['wav'], spec=analog['spec'])))
    try:
        analog_source_final = ColumnDataSource(data=copy.deepcopy(analog_sources_raw[0].data))
    except IndexError:
        analog_source_final = ColumnDataSource(data=dict(wav=[], spec=[]))
    if 'reflect' in spec_type:
        if not reflec:
            raw_plot.line('wav', 'spec', source=analog_source_final, color="firebrick")
            raw_plot.title.text = 'Object: {}    Analog: {}'.format(data_spec[0]['label'], analog_data[0]['label'])
        # Build Reflectance Plot
        spec_dict = read_mean_tax()
        spec_dict["Wavelength"] = [l*10000 for l in spec_dict["Wavelength"]]

        stand_list = ['A', 'B', 'C', 'D', 'K', 'L', 'O', 'Q', 'S', 'Sq', 'T', 'V', 'X', 'Xe']
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

            ref_plot.line("Wavelength", tax+"_Mean", source=source, color=colors[j], name=tax + "-Type", line_width=2,
                          line_dash='dashed', legend_label=tax, visible=vis)
            if np.mean(spec_dict[tax + '_Sigma']) > 0:
                ref_plot.patch(xs, ys, fill_alpha=.25, line_width=1, fill_color=colors[j], line_color="black",
                               name=tax + "-Type", legend_label=tax, line_alpha=.25, visible=vis)

        if not reflec:
            for spec in data_spec:
                reflectance_sources = []
                for a in analog_data:
                    data_label_reflec, reflec_spec, reflec_ast_wav, reflec_ast_err = spectrum_plot(spec['filename'], analog=a['filename'])
                    lower_error = np.array([flux - reflec_ast_err[i] for i, flux in enumerate(reflec_spec)])
                    upper_error = np.array([flux + reflec_ast_err[i] for i, flux in enumerate(reflec_spec)])
                    reflectance_sources.append(ColumnDataSource(data=dict(wav=reflec_ast_wav, spec=reflec_spec, up=upper_error, low=lower_error)))
                reflect_source_prefs.append(ColumnDataSource(data=copy.deepcopy(reflectance_sources[0].data)))
                reflect_source_lists.append(reflectance_sources)
            for k, ref_source in enumerate(reflect_source_prefs):
                reflectance_lines.append(ref_plot.line("wav", "spec", source=ref_source, line_width=3, name=data_spec[k]['label']))
                # More work is needed to make spectroscopic error bars feasible. the following will only behave properly for 1 frame of 1 analog.
                # reflectance_lines.append(ref_plot.line("wav", "up", source=ref_source, line_width=1, name=data_spec[k]['label']))
                # reflectance_lines.append(ref_plot.line("wav", "low", source=ref_source, line_width=1, name=data_spec[k]['label']))
            ref_plot.title.text = 'Object: {}    Analog: {}'.format(data_spec[0]['label'], analog_data[0]['label'])
        else:
            for spec in data_spec:
                ref_plot.circle(spec['wav'], spec['spec'], size=3, name=spec['label'])
            title = data_spec[0]['label']
            for d in data_spec:
                if d['label'] != title:
                    chunks = d['label'].split("--")
                    title += ' /' + chunks[1]
            ref_plot.title.text = 'Object: {}'.format(title)

        hover = HoverTool(tooltips="$name", point_policy="follow_mouse", line_policy="none")

        ref_plot.add_tools(hover)
        ref_plot.legend.click_policy = 'hide'
        ref_plot.legend.orientation = 'horizontal'

        # set axes
        ref_plot.axis.axis_line_width = 2
        ref_plot.axis.axis_label_text_font_size = "12pt"
        ref_plot.axis.major_tick_line_width = 2
        ref_plot.xaxis.axis_label = "Wavelength (Å)"
        ref_plot.yaxis.axis_label = 'Reflectance Spectra (Normalized at 5500 Å)'

    # Build tools
    if analog_data:
        analog_labels = [a['label'] for a in analog_data]
    else:
        analog_labels = ["--None--"]

    analog_select = Select(title="Analog", value=analog_labels[0], options=analog_labels)
    frame_labels = list(map(str, range(1, len(data_spec)+1)))
    frame_select = MultiSelect(title="Target Frames", value=frame_labels, options=frame_labels, height=49, width=100)

    # JS Call back to change analog
    js_analog_picker = get_js_as_text(js_file, "analog_select")
    analog_select_callback = CustomJS(args=dict(analog_select=analog_select, frame_select=frame_select,
                                                reflectance_sources=reflect_source_lists,
                                                chosen_sources=reflect_source_prefs, plot=raw_plot, plot2=ref_plot,
                                                lines=reflectance_lines, raw_analog=analog_source_final,
                                                raw_analog_list=analog_sources_raw, raw_lines=raw_lines),
                                      code=js_analog_picker)
    analog_select.js_on_change('value', analog_select_callback)
    frame_select.js_on_change('value', analog_select_callback)

    selector_row = row(frame_select, analog_select)
    layouts = {'raw_and_reflect': column(selector_row, row(ref_plot), row(raw_plot)),
               'raw_only': column(selector_row, row(raw_plot)),
               'raw_standard': column(row(raw_plot)),
               'reflect_only': column(row(ref_plot))
               }

    # Create script/div
    script, div = components(layouts[spec_type], CDN)

    chunks = div.split("data-root-id=")
    named_div = chunks[0] + f'name="spec_plot" data-root-id=' + chunks[1]

    return script, named_div


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
        obj_up_emp = dark_and_object_up(emp, d, d + timedelta(days=1), 0, alt_limit=alt_limit)
        vis_time, emp_obj_up, set_time = compute_dark_and_up_time(obj_up_emp, step_size)
        obj_set = datetime_to_radians(d, set_time)
        dark_and_up_time, max_alt, up_time, down_time = get_visibility(None, None, d + timedelta(days=bonus_day), site, step_size, alt_limit, False, body_elements)
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
        new_x.append(-1 + i * (2 / (len(site_list)-1)))
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
    plot.wedge(x='x', y='y', radius=rad, start_angle="obj_rise", end_angle="obj_set", color="colors", line_color="black", line_alpha="line_alpha", source=source)
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
    """Pulls an object name from the ALCDEF metadata."""

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


def get_js_as_text(file, funct):
    """Pull out given function from js file and convert to text for Bokeh
    Inputs:
        file: Absolute path to js file containing desired function
        funct: name of function to be imported into Bokeh Callback
    """
    with open(file, "r") as js:
        lines = js.readlines()
    js_text = ''
    print_js = False
    for line in lines:
        if print_js and (line == '}\n' or line == '}'):
            break
        if print_js:
            js_text += line
        if "function {}(".format(funct) in line:
            print_js = True
    return js_text


class RotTool(Tool):
    """Create Bokeh Tool for tracking 3D rotation with mouse movement.
        Add to plot with RotTool(source, obs, orbs)
            source:..DataSource with data:(x=[] and y=[]). Used to track change in mouse position from move to move.
            obs:.....1st data set to be looped through. Must contain equal length datasets with names formatted  as
                     "<name>_[x,y,z]". Any columns without this formatting will be skipped, while x,y,z datasets will be
                     transformed.
            orbs:....2nd independent DataSource of equal length data sets using same format as obs.
    """
    TS_CODE = get_js_as_text(js_file, "rotation_tool")
    __implementation__ = TypeScript(TS_CODE)
    source = Instance(ColumnDataSource)
    coords_list = List(Instance(ColumnDataSource))


def lc_plot(lc_list, meta_list, lc_model_dict={}, period=1, pscan_list=[], shape_model_dict=[], pole_vector=[], body=None, jpl_ephem=None):
    """Creates an interactive Bokeh LC plot:
    Inputs:
    [lc_list] --- A list of LC dictionaries, each one containing the following keys:
            ['date'] --- A list of Julian Dates corresponding to each observation
            ['mags'] --- a list of magnitudes corresponding to each date
            ['mag_errs'] --- a list of magnitude errors corresponding to each magnitude
    [meta_list] --- a list of dictionaries with the same length as [lc_list] each containing at leas the following keys:
            ['SESSIONDATE'] --- Date string with the format '%Y-%m-%d' corresponding to the UT day of observation block
            ['SESSIONTIME'] --- Time string with the format 'H:%M:%S' corresponding to the UT time of observation block
            ['OBJECTNAME'] --- Name of target
            ['OBJECTNUMBER'] --- Number of target
            ['MPCDESIG'] --- Provisional Designation of target
            ['FILTER'] --- Filter of Observation
            ['MPCCODE'] --- Sitecode of observation
    period --- length in hours of the predicted period (float)
    jpl_ephem --- AstroPy Table containing at least the following keys:
            ['datetime_jd'] --- Julian dates
            ['V'] --- predicted V magnitude for given Julian dates
    """

    # Pull general info from metadata
    if body is None:
        obj, name, num = get_name(meta_list[0])
    else:
        obj = body.current_name()
    date_range = meta_list[0]['SESSIONDATE'].replace('-', '') + '-' + meta_list[-1]['SESSIONDATE'].replace('-', '')
    base_date = floor(min(sorted([jd for lc in lc_list for jd in lc['date']])))

    # Initialize plots
    plot_u = figure(plot_width=900, plot_height=400)
    plot_p = figure(plot_width=900, plot_height=400)
    plot_u.y_range.flipped = True
    plot_u.y_range.only_visible = True
    plot_p.x_range = Range1d(0, 1.1, bounds=(-.2, 1.2))
    plot_p.y_range = DataRange1d(names=['mags'], flipped=True)
    plot_period = figure(plot_width=900, plot_height=400)
    plot_period.y_range = DataRange1d(names=['period'])
    plot_period.x_range = DataRange1d(names=['period'], bounds=(0, None))
    plot_orbit = figure(plot_width=900, plot_height=900, x_axis_location=None, y_axis_location=None)
    if body.meandist:
        orbit_range = body.meandist
    elif body.perihdist:
        orbit_range = body.perihdist
    else:
        orbit_range = 1
    plot_orbit.y_range = Range1d(min(-1.1, -1.1 * orbit_range), max(1.1, 1.1 * orbit_range))
    plot_orbit.x_range = Range1d(min(-1.1, -1.1 * orbit_range), max(1.1, 1.1 * orbit_range))
    plot_orbit.grid.grid_line_color = None
    plot_shape = figure(plot_width=600, plot_height=600, x_axis_location=None, y_axis_location=None)
    plot_shape.grid.grid_line_color = None
    plot_shape.background_fill_color = "#0e122a"
    plot_shape.y_range = Range1d(-2.1, 2.1)
    plot_shape.x_range = Range1d(-2.1, 2.1)

    # Create Column Data Source that will be used by the plots
    source = ColumnDataSource(data=dict(time=[], mag=[], color=[], title=[], err_high=[], err_low=[], alpha=[]))  # phased LC data Source
    orig_source = ColumnDataSource(data=dict(time=[], mag=[], mag_err=[], color=[], title=[], err_high=[], err_low=[], alpha=[]))  # unphased LC data source
    dataset_source = ColumnDataSource(data=dict(symbol=[], date=[], time=[], site=[], filter=[], color=[], title=[], offset=[]))  # dataset info
    horizons_source = ColumnDataSource(data=dict(date=[], v_mag=[]))  # V-mag info
    periodogram_sources = []
    for peri in pscan_list:
        periodogram_sources.append(ColumnDataSource(data=peri))  # periodogram info
    p_mark_source = ColumnDataSource(data=dict(period=[period], y=[-1]))
    orbit_source = ColumnDataSource(data=get_orbit_position(meta_list, lc_list, body))
    full_orbit_source = ColumnDataSource(data=get_full_orbit(body))
    shape_sources = []
    for shape in shape_model_dict:
        shape_sources.append(ColumnDataSource(data=shape))
    pole_sources = []
    for pvec in pole_vector:
        pole_sources.append(ColumnDataSource(data=pvec))
    prev_rot_source = ColumnDataSource(data=dict(prev_rot=[0]*len(shape_model_dict)))
    lc_models_sources = []
    model_names_unique = list(set(lc_model_dict['name']))
    model_list_source = ColumnDataSource(data=dict(name=model_names_unique, offset=[0]*len(model_names_unique)))
    for k, lc_name in enumerate(lc_model_dict['name']):
        model_date = [(x - base_date) * 24 for x in lc_model_dict['date'][k]]
        lc_models_sources.append(ColumnDataSource(data=dict(date=model_date, mag=lc_model_dict['mag'][k], name=[lc_name]*len(model_date), omag=lc_model_dict['mag'][k], alpha=[0]*len(model_date))))

    # Create Input controls
    phase_shift = Slider(title="Phase Offset", value=0, start=-1, end=1, step=.01, width=200, tooltips=False)  # Slider bar to change base_date by +/- 1 period
    max_period = max(round(10 * period), 1)
    min_period = 0.0
    step = (max_period - min_period)/1000
    period_slider = Slider(title=None, value=period, start=min_period, end=max_period, step=step, width=200, tooltips=False)  # Slider bar to change period
    if period != 1:
        p_box_title = 'Period (Default: {}h)'.format(period)
    else:
        p_box_title = 'Period (Unknown)'
    period_box = Spinner(value=period, low=0, step=step, title=p_box_title, width=200)  # Number Box for typing in period
    p_slider_min = Spinner(value=min_period, low=0, step=.01, title="min", width=100)  # Number box for setting period constraints
    p_slider_max = Spinner(value=max_period, low=0, step=.01, title="max", width=100)  # Number box for setting period constraints
    v_offset_button = Toggle(label="Apply Predicted Offset", button_type="default")  # Button to add/remove Horizons predicted offset
    draw_button = Button(label="Re-Draw", button_type="default", width=50)  # Button to re-draw mags.
    model_draw_button = Button(label="Re-Draw", button_type="default", width=50)  # Button to re-draw models.
    contrast_switch = Toggle(label="Remove Shading", button_type="default")  # Change lighting contrast
    orbit_slider = Slider(title="Orbital Phase", value=0, start=-1, end=1, step=.01, width=200, tooltips=True)
    rotation_slider = Slider(title="Rotational Phase", value=0, start=-2, end=2, step=.01, width=200, tooltips=True)
    shape_labels = [str(x+1) for x in range(len(shape_model_dict))]
    shape_select = Select(title="Shape Model", value='1', options=shape_labels)

    # Create plots
    error_cap = TeeHead(line_alpha=0)
    # Build unphased plot:
    plot_u.line(x="date", y="v_mag", source=horizons_source, line_color='black', line_width=3, line_alpha=.5, legend_label="Horizons V-mag", visible=False)
    model_lines = []
    for n, s in enumerate(lc_models_sources):
        model_lines.append(plot_u.line(x="date", y="mag", source=s, name=lc_model_dict['name'][n], visible=False, line_color='firebrick', line_width=2, line_alpha=.5))
    plot_u.add_layout(
        Whisker(source=orig_source, base="time", upper="err_high", lower="err_low", line_color="color", line_alpha="alpha",
                lower_head=error_cap, upper_head=error_cap))
    plot_u.circle(x="time", y="mag", source=orig_source, size=3, color="color", alpha="alpha")
    plot_u.legend.click_policy = 'hide'

    # Build Phased PLot:
    plot_p.add_layout(
        Whisker(source=source, base="time", upper="err_high", lower="err_low", line_color="color", line_alpha="alpha",
                lower_head=error_cap, upper_head=error_cap))
    data_plot = plot_p.circle(x="time", y="mag", source=source, size=3, color="color", alpha="alpha", name='mags')
    base_line = plot_p.line([-2, 2], [base_date, base_date], alpha=0, name="phase_line")

    # Build periodogram:
    period_data = []
    for ps in periodogram_sources:
        period_data.append(plot_period.line(x="period", y="chi2", source=ps, color="red", name='period'))
    period_mark = plot_period.ray(x="period", y="y", length=10, angle=pi/2, source=p_mark_source, line_width=2)

    # Build orbit plot:
    ast_pos = plot_orbit.circle(x="a_x", y="a_y", source=orbit_source, color="red", name=body.full_name())
    earth_pos = plot_orbit.circle(x="e_x", y="e_y", source=orbit_source, name="Earth")
    sun_pos = plot_orbit.circle([0], [0], size=10, color="black")
    ast_orbit = plot_orbit.line(x="asteroid_x", y="asteroid_y", source=full_orbit_source, color="gray")
    for planet in get_planetary_elements():
        plot_orbit.line(x=f"{planet}_x", y=f"{planet}_y", source=full_orbit_source, color="gray", alpha=.5)
    cursor_change_source = ColumnDataSource(data=dict(x=[], y=[]))
    plot_orbit.add_tools(RotTool(source=cursor_change_source, coords_list=[full_orbit_source, orbit_source]))

    # Build shape model
    shape_patches = []
    for n, shape in enumerate(shape_sources):
        if n == 0:
            shape_vis = True
        else:
            shape_vis = False
        shape_patches.append(plot_shape.patches(xs="faces_x", ys="faces_y", source=shape, color="faces_colors", visible=shape_vis))
    shape_rot_source_list = shape_sources + pole_sources
    plot_shape.add_tools(RotTool(source=cursor_change_source, coords_list=shape_rot_source_list))
    shape_label_source = ColumnDataSource(data=dict(x=[10, 10, 555, 555, 10, 10], y=[565, 545, 565, 545, 35, 15],
                                                    align=['left', 'left', 'right', 'right', 'left', 'left'],
                                                    text=['Pole Orientation:',
                                                          f'({round(degrees(pole_vector[0]["p_long"][0]),1)}, {round(degrees(pole_vector[0]["p_lat"][0]) + 90,1)})',
                                                          'Heliocentric Position:',
                                                          f'({round(body.longascnode, 1)}, 0.0)',
                                                          'Sidereal Period:',
                                                          f'{pole_vector[0]["period_fit"][0]}h']))
    pole_label = LabelSet(x='x', y='y', x_units='screen', y_units='screen', text='text', text_align='align', source=shape_label_source,
                          render_mode='css', text_color='limegreen')
    plot_shape.add_layout(pole_label)

    # Write custom JavaScript Code to print the time to the next iteration of the given phase in a HoverTool
    js_hover_text = get_js_as_text(js_file, "next_time_phased")
    next_time = CustomJSHover(args=dict(period_box=period_box, phase_shift=phase_shift), code=js_hover_text)

    # Build Hovertools
    hover1 = HoverTool(tooltips=[('Phase', '$x{0.000}'), ('Mag', '$y{0.000}'), ('To Next', '@y{custom}')],
                       formatters={'@y': next_time}, point_policy="none", line_policy="none", show_arrow=False,
                       mode="vline", renderers=[base_line], attachment='above')
    hover2 = HoverTool(tooltips='@title', renderers=[data_plot], point_policy="snap_to_data", attachment='below')
    period_hover = HoverTool(tooltips='$x{0.0000}', renderers=period_data, point_policy="none", mode="vline",
                             line_policy="none", attachment='above')
    crosshair = CrosshairTool()
    plot_p.add_tools(hover1, crosshair, hover2)
    plot_period.add_tools(period_hover, crosshair)

    # Set Axis and Title Text
    plot_u.yaxis.axis_label = 'Apparent Magnitude'
    plot_u.title.text = 'LC for {} ({})'.format(obj, date_range)

    plot_p.yaxis.axis_label = 'Apparent Magnitude'
    plot_p.title.text = 'LC for {} ({})'.format(obj, date_range)
    plot_p.xaxis.axis_label = 'Phase (Period = {}h / Epoch = {})'.format(period, base_date)
    plot_period.title.text = f'Periodogram for {obj}'
    plot_period.xaxis.axis_label = "Period (h)"
    plot_period.yaxis.axis_label = "Chi^2"
    # plot_p.title.text_font_size = '20pt'
    # plot_p.xaxis.axis_label_text_font_size = "18pt"
    # plot_p.yaxis.axis_label_text_font_size = "18pt"
    # plot_p.axis.axis_line_width = 2
    # plot_p.yaxis.major_label_text_font_size = "14pt"
    # plot_p.xaxis.major_label_text_font_size = "14pt"
    # plot_p.axis.major_tick_line_width = 2
    # plot_u.title.text_font_size = '20pt'
    # plot_u.xaxis.axis_label_text_font_size = "18pt"
    # plot_u.yaxis.axis_label_text_font_size = "18pt"
    # plot_u.axis.axis_line_width = 2
    # plot_u.yaxis.major_label_text_font_size = "14pt"
    # plot_u.xaxis.major_label_text_font_size = "14pt"
    # plot_u.axis.major_tick_line_width = 2
    plot_p.xaxis.axis_label = 'Phase (Period = {}h / Epoch = {})'.format(period, base_date)

    # Create update function to fill datasets. This is currently unnecessary, but could be used if we ever got a
    # Bokeh Server up and running. Then we would run this function instead of all of the JS below
    def update():
        sess_date = []
        sess_time = []
        sess_filt = []
        sess_site = []
        sess_title = []
        sess_color = []
        sess_url = []
        span = []
        jpl_v_mid = []
        phased_lc_list = phase_lc(copy.deepcopy(lc_list), period, base_date)
        unphased_lc_list = phase_lc(copy.deepcopy(lc_list), None, base_date)
        try:
            jpl_date = (jpl_ephem['datetime_jd'] - base_date) * 24
            try:
                horizons_source.data = dict(date=jpl_date, v_mag=jpl_ephem['V'])
            except KeyError:
                horizons_source.data = dict(date=jpl_date, v_mag=jpl_ephem['Tmag'])
        except TypeError:
            jpl_date = []
            horizons_source.data = dict(date=[], v_mag=[])
        colors = itertools.cycle(Category20[20])
        for c, lc in enumerate(phased_lc_list):
            plot_col = next(colors)
            plot_col = next(colors)
            plot_col = next(colors)
            # Build dataset_title
            sess_mid = (unphased_lc_list[c]['date'][-1] + unphased_lc_list[c]['date'][0]) / 2
            try:
                jpl_v_mid.append(np.interp(sess_mid, jpl_date, horizons_source.data['v_mag']))
            except ValueError:
                jpl_v_mid.append(0)
            span.append(round((unphased_lc_list[c]['date'][-1] - unphased_lc_list[c]['date'][0]), 2))
            md = meta_list[c]
            sess_date.append(md['SESSIONDATE'])
            sess_time.append(md['SESSIONTIME'])
            filt = translate_from_alcdef_filter(md['FILTER'])
            sess_filt.append(filt)
            sess_site.append(md['MPCCODE'])
            sess_url.append(md['alcdef_url'])
            sess_color.append(plot_col)
            dataset_title = "{}T{} -- Filter:{} -- Site:{}".format(md['SESSIONDATE'], md['SESSIONTIME'], filt, md['MPCCODE'])
            sess_title.append(dataset_title)
        sess_sym = ['&#10739;']*len(sess_date)
        offset = [0]*len(sess_date)
        dataset_source.data = dict(symbol=sess_sym, date=sess_date, time=sess_time, site=sess_site, filter=sess_filt, color=sess_color, title=sess_title, offset=offset, span=span, v_mid=jpl_v_mid, url=sess_url)

        phased_dict = build_data_sets(phased_lc_list, sess_title)
        for k, phase in enumerate(phased_dict['time']):
            if 0 < phase < 1:
                for key in phased_dict.keys():
                    if key == 'time':
                        if 0 < phase < 0.5:
                            phased_dict['time'].append(phase + 1)
                        elif 0.5 < phase < 1:
                            phased_dict['time'].append(phase - 1)
                    else:
                        phased_dict[key].append(phased_dict[key][k])
        source.data = phased_dict
        orig_source.data = build_data_sets(unphased_lc_list, sess_title)

    update()  # initial load of the data

    # set up variable x_axis on unphased plot
    uplot_min = min(orig_source.data['time'])
    uplot_max = max(orig_source.data['time'])
    uplot_buffer = (uplot_max - uplot_min) * .1
    uplot_min = uplot_min - uplot_buffer
    uplot_max = uplot_max + uplot_buffer
    plot_u.x_range = Range1d(uplot_min, uplot_max)
    # Establish initial ranges
    plot_u.extra_x_ranges = {"days": Range1d(uplot_min / 24, uplot_max / 24),
                             "hours": Range1d(uplot_min, uplot_max),
                             "mins": Range1d(uplot_min * 60, uplot_max * 60)}
    # Build new axes
    plot_u.add_layout(LinearAxis(x_range_name='days', visible=False,
                                 axis_label=f'Date (Days from {jd_utc2datetime(base_date).strftime("%Y-%m-%d")}.5/{base_date}.0)'), 'below')
    plot_u.add_layout(LinearAxis(x_range_name='mins', visible=False,
                                 axis_label=f'Date (Minutes from {jd_utc2datetime(base_date).strftime("%Y-%m-%d")}.5/{base_date}.0)'), 'below')
    plot_u.below[0].x_range_name = 'hours'
    plot_u.below[0].visible = False
    plot_u.below[0].axis_label = f'Date (Hours from {jd_utc2datetime(base_date).strftime("%Y-%m-%d")}.5/{base_date}.0)'
    # Set visible axis
    if uplot_max < .5:
        plot_u.below[2].visible = True
    elif uplot_max < 200:
        plot_u.below[0].visible = True
    else:
        plot_u.below[1].visible = True
    # Set up JS to change axes on zoom
    u_plot_x_axis_js = get_js_as_text(js_file, "u_plot_xaxis_scale")
    u_plot_x_axis_callback = CustomJS(args=dict(plot=plot_u), code=u_plot_x_axis_js)
    plot_u.x_range.js_on_change('end', u_plot_x_axis_callback)

    # Create HTML template format that allows printing of data symbol
    template = """
                <p style="color:<%=
                    (function colorfromint(){
                        return(color)
                    }()) %>;">
                    <%= value %>
                </p>
                """
    formatter = HTMLTemplateFormatter(template=template)

    # Establish Columns for DataTable
    columns_lc = [
        TableColumn(field="symbol", title='', formatter=formatter, width=3),
        TableColumn(field="date", title="Date", formatter=HTMLTemplateFormatter(template='<a href="<%= (url) %>"target="_blank"><%= value %> </a>')),
        TableColumn(field="time", title="Time"),
        TableColumn(field="span", title="Span (h)", formatter=NumberFormatter(format="0.00")),
        TableColumn(field="site", title="Site"),
        TableColumn(field="filter", title="Filter"),
        TableColumn(field="offset", title="Mag Offset", editor=NumberEditor(step=.1), formatter=NumberFormatter(format="0.00"))
    ]
    columns_model = [
        TableColumn(field="name", title="Name"),
        TableColumn(field="offset", title="Mag Offset", editor=NumberEditor(step=.1),
                    formatter=NumberFormatter(format="0.00"))
    ]

    # Build Datatable and Title
    dataset_source.selected.indices = list(range(len(dataset_source.data['date'])))
    data_table = DataTable(source=dataset_source, columns=columns_lc, width=600, height=300, selectable='checkbox', index_position=None, editable=True)
    table_title = Div(text='<b>LC Data</b>', width=450)  # No way to set title for Table, Have to build HTML Div and put above it...
    model_table = DataTable(source=model_list_source, columns=columns_model, width=300, height=300, selectable='checkbox', index_position=None, editable=True)
    model_table_title = Div(text='<b>Models</b>', width=450)

    # JS Callback to set Dataset Mag offset to relative Horizons v-mag differences
    js_mag_offset = get_js_as_text(js_file, "set_mag_offset")
    v_offset_callback = CustomJS(args=dict(dataset_source=dataset_source, toggle=v_offset_button), code=js_mag_offset)
    v_offset_button.js_on_click(v_offset_callback)

    # JS Callback to update phased data when datasets are removed, and mag offsets are made.
    # Note: Data just hidden (set to alpha=0). Not actually removed.
    js_remove_shift_data = get_js_as_text(js_file, "remove_shift_data")
    callback = CustomJS(args=dict(source=source, dataset_source=dataset_source, osource=orig_source, plot=plot_p, plot2=plot_u), code=js_remove_shift_data)
    dataset_source.selected.js_on_change('indices', callback)
    draw_button.js_on_click(callback)
    dataset_source.js_on_change('data', callback)  # Does not seem to work. Not sure why.

    # JS Callback to plot and adjust models on unphased plots
    js_remove_shift_model = get_js_as_text(js_file, "remove_shift_model")
    model_callback = CustomJS(args=dict(source_list=lc_models_sources, model_source=model_list_source, lines=model_lines), code=js_remove_shift_model)
    model_list_source.selected.js_on_change('indices', model_callback)
    model_draw_button.js_on_click(model_callback)
    model_list_source.js_on_change('data', model_callback)

    # JS Call back to handle period max and min changes to both the period_box and the period_slider
    # Self validation (min < 0, for instance) does not seem to work properly.
    js_period_linker = get_js_as_text(js_file, "link_period")
    period_bounds_callback = CustomJS(args=dict(period_box=period_box, period_slider=period_slider, p_max=p_slider_max, p_min=p_slider_min), code=js_period_linker)
    p_slider_max.js_on_change('value', period_bounds_callback)
    p_slider_min.js_on_change('value', period_bounds_callback)

    # Link period_slider to period_box
    period_slider.js_link('value', period_box, 'value')

    # JS call back to handle phasing of data to given period/epoch
    js_phase_data = get_js_as_text(js_file, "phase_data")
    phased_callback = CustomJS(args=dict(source=source, period_box=period_box, period_slider=period_slider, plot=plot_p,
                                         osource=orig_source, phase_shift=phase_shift, base_date=base_date,
                                         p_mark_source=p_mark_source), code=js_phase_data)
    period_box.js_on_change('value', phased_callback)
    phase_shift.js_on_change('value', phased_callback)

    # JS for Shape Model
    js_switch_contrast = get_js_as_text(js_file, "contrast_switch")
    contrast_callback = CustomJS(args=dict(toggle=contrast_switch, plots=shape_patches),
                                 code=js_switch_contrast)
    contrast_switch.js_on_click(contrast_callback)

    js_shading = get_js_as_text(js_file, "shading_slider")
    shading_callback = CustomJS(args=dict(source=shape_sources, orbit_slider=orbit_slider, rot_slider=rotation_slider,
                                          long_asc=radians(body.longascnode), inc=radians(body.orbinc), sn=shape_select,
                                          prev_rot=prev_rot_source, orient=pole_sources, label=shape_label_source),
                                code=js_shading)
    orbit_slider.js_on_change('value', shading_callback)
    rotation_slider.js_on_change('value', shading_callback)

    js_shape_selector = get_js_as_text(js_file, "shape_select")
    shape_select_callback = CustomJS(args=dict(selector=shape_select, plots=shape_patches, labels=shape_label_source,
                                               poles=pole_vector),
                                     code=js_shape_selector)
    shape_select.js_on_change('value', shape_select_callback)

    # Build layout tables:
    phased_layout = column(plot_p,
                           row(column(row(table_title),
                                      data_table,
                                      row(v_offset_button, draw_button)),
                               column(row(column(row(period_box),
                                                 period_slider,
                                                 phase_shift),
                                          column(p_slider_min,
                                                 p_slider_max)))))
    unphased_layout = column(plot_u,
                             row(column(row(table_title),
                                        data_table),
                                 column(row(model_table_title),
                                        model_table, model_draw_button)))
    periodogram_layout = column(plot_period,
                                row(column(row(table_title),
                                           data_table),
                                    column(row(column(row(period_box),
                                                      period_slider),
                                               column(p_slider_min,
                                                      p_slider_max)))))
    orbit_layout = column(plot_orbit)
    shape_layout = column(row(plot_shape, column(shape_select,
                                                 orbit_slider,
                                                 rotation_slider,
                                                 contrast_switch)))

    # Set Tabs
    tabu = Panel(child=unphased_layout, title="Unphased")
    tabp = Panel(child=phased_layout, title="Phased")
    tab_list = [tabu, tabp]
    if pscan_list[0]['period']:
        tab_per = Panel(child=periodogram_layout, title="Periodogram")
        tab_list.append(tab_per)
    tab_orb = Panel(child=orbit_layout, title="Orbital Diagram")
    tab_list.append(tab_orb)
    if shape_model_dict:
        tab_shape = Panel(child=shape_layout, title="Asteroid Shape")
        tab_list.append(tab_shape)
    tabs = Tabs(tabs=tab_list)

    script, div = components({'plot': tabs}, CDN)
    chunks = div['plot'].split("data-root-id=")
    div['plot'] = chunks[0] + f'name="lc_plot" data-root-id=' + chunks[1]

    return script, div


def build_data_sets(lc_list, title_list):
    """Buld initial datasources"""
    x_times = []
    y_mags = []
    mag_err = []
    hi_errs = []
    low_errs = []
    dat_colors = []
    dat_alphas = []
    data_title = []
    colors = itertools.cycle(Category20[20])
    for c, lc in enumerate(lc_list):
        plot_col = next(colors)
        plot_col = next(colors)
        plot_col = next(colors)
        # Build Error Bars
        err_up = np.array(lc['mags']) + np.array(lc['mag_errs'])
        err_low = np.array(lc['mags']) - np.array(lc['mag_errs'])

        # Build source data
        x_times += lc['date']
        y_mags += lc['mags']
        mag_err += lc['mag_errs']
        hi_errs += list(err_up)
        low_errs += list(err_low)
        dat_colors += [plot_col]*len(lc['date'])
        dat_alphas += [1]*len(lc['date'])

        # Build dataset_title
        dataset_title = title_list[c]
        data_title += [dataset_title]*len(lc['date'])
    data = dict(time=x_times, mag=y_mags, color=dat_colors, title=data_title, err_high=hi_errs,
                            err_low=low_errs, alpha=dat_alphas, mag_err=mag_err)
    return data


def get_orbit_position(meta_list, lc_list, body):
    body_elements = model_to_dict(body)
    dates = []
    hcnt_a_x = []
    hcnt_a_y = []
    hcnt_a_z = []
    hcnt_e_x = []
    hcnt_e_y = []
    hcnt_e_z = []
    for k, dat in enumerate(meta_list):
        site = dat['MPCCODE']
        if len(lc_list[k]['date']) > 2:
            date_list = [lc_list[k]['date'][0], lc_list[k]['date'][-1]]
        else:
            date_list = lc_list[k]['date']
        for c, d in enumerate(date_list):
            ephem_date = jd_utc2datetime(d)
            dates.append(ephem_date)
            ephem = compute_ephem(ephem_date, body_elements, site)
            geocnt_a_pos = ephem["geocnt_a_pos"]
            heliocnt_e_pos = ephem["heliocnt_e_pos"]
            heliocnt_a_pos = [x_a + x_g for x_a, x_g in zip(geocnt_a_pos, heliocnt_e_pos)]
            hcnt_a_x.append(heliocnt_a_pos[0])
            hcnt_a_y.append(heliocnt_a_pos[1])
            hcnt_a_z.append(heliocnt_a_pos[2])
            hcnt_e_x.append(heliocnt_e_pos[0])
            hcnt_e_y.append(heliocnt_e_pos[1])
            hcnt_e_z.append(heliocnt_e_pos[2])

    position_data = dict(time=dates, a_x=hcnt_a_x, a_y=hcnt_a_y, a_z=hcnt_a_z, e_x=hcnt_e_x, e_y=hcnt_e_y, e_z=hcnt_e_z)
    return position_data


def get_full_orbit(body):
    body_elements = model_to_dict(body)
    full_orbit = [orbital_pos_from_true_anomaly(nu, body_elements) for nu in np.arange(-pi, pi, .01)]
    full_orbit_x = [pos[0] for pos in full_orbit]
    full_orbit_y = [pos[1] for pos in full_orbit]
    full_orbit_z = [pos[2] for pos in full_orbit]
    position_data = dict(asteroid_x=full_orbit_x, asteroid_y=full_orbit_y, asteroid_z=full_orbit_z)

    planetary_elements = get_planetary_elements()
    for planet in planetary_elements:
        p_orb = [orbital_pos_from_true_anomaly(nu, planetary_elements[planet]) for nu in np.arange(-pi, pi, .01)]
        position_data[f'{planet}_x'] = [pos[0] for pos in p_orb]
        position_data[f'{planet}_y'] = [pos[1] for pos in p_orb]
        position_data[f'{planet}_z'] = [pos[2] for pos in p_orb]
    return position_data


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


def translate_from_alcdef_filter(filt):
    if filt not in 'B, V, R, I, J, H, K':
        filt = filt.lower()
        if len(filt) > 1 and filt[0] == 's':
            filt = filt[1] + 'p'
        elif filt == 'c':
            filt = 'Clear'
    return filt

def generalized_fwhm_plotter(blocks_or_ref_fields, filters, colors, output_dir, individual_block_plots, make_full_night_plot):
    """Plots full width half maxima against time for each filter in a block or group of blocks over the blocks' observation nights.
    Pass a block, list/Queryset of blocks, reference field, or list/Queryset of reference fields through \<blocks_or_ref_fields\>.
    If a single block is passed, it will be thrown into a one element list. If a list or Queryset of blocks is passed, all elements
    will be thrown into a new list. If a reference field is passed, function will find all blocks in the reference field and throw them
    into a list. The same process will be done for a list of reference fields; all reference will be looped over and have their blocks
    extracted + thrown into the same list. No matter which of the four options is passed, it will be configured into a list of blocks.
    Pass an np array or list of \<filters\> for which to plot fwhm, and a corresponding list or np array of colors for which the color
    matches the filter at its same index. This determines the color coding and legends for the plot. Select an \<output_dir\> as an output
    directory to save the figure(s). Finally, select True or False for \<individual_block_plots\> and \<make_full_night_plot\>. If
    \<individual_block_plots\> is true, an individual plot of fwhms for all filters will be made for each block (unique date + ref field combo).
    If <\make_full_night_plot\> is True, it will make a plot for a night of observation; if multiple blocks fall on this night they will appear as
    subplots labelled by their corresponding reference field. If there are more than 5 blocks sharing a night of observation, multiple
    plots will be made for the night, each with 5 subplots in chronological order representing each block. If #blocks % 5 != 0, the final
    plot will contain as many subplots as there are blocks in the remainder. The separate plots will be numbered in chronological order,
    (i.e. first 5 blocks chronologically = plot 1, second 5 blocks= plot 2, ...). If \<individual_block_plots\> and \<make_full_night_plot\>
    are True, both actions will be executed. If both are false, function defaults to \<make_full_night_plot\> = True. If there is only one block,
    \<individual_block_plots\> defaults to true and \<make_full_night_plot\> defaults to false to save computational time, since for one block
    they do the same thing and individual block plots are faster. """
    filenames = []
    #determine datatype given and extract corresponding blocks
    if type(filters) != np.ndarray:
        filters = np.array(filters)
    if type(colors) != np.ndarray:
        colors = np.array(colors)
    try:
        blocks = []
        if isinstance(blocks_or_ref_fields[0], core.models.sources.StaticSource) == True:
            ref_fields = blocks_or_ref_fields
            for ref_field in ref_fields:
                from_statsource_get_blocks = Block.objects.filter(calibsource = ref_field).order_by('block_start')
                obs_blocks = from_statsource_get_blocks.filter(num_observed__gte=1)
                for item in obs_blocks:
                    blocks.append(item)
        elif isinstance(blocks_or_ref_fields[0], core.models.blocks.Block) == True:
            blockset = blocks_or_ref_fields
            for item in blockset:
                blocks.append(item)
    except TypeError:
        if isinstance(blocks_or_ref_fields, core.models.blocks.Block) == True:
            blocks = [blocks_or_ref_fields]
        elif isinstance(blocks_or_ref_fields, core.models.sources.StaticSource) == True:
            blocks = []
            from_statsource_get_blocks = Block.objects.filter(calibsource = blocks_or_ref_fields).order_by('block_start')
            obs_blocks = from_statsource_get_blocks.filter(num_observed__gte=1)
            for item in obs_blocks:
                blocks.append(item)
    if len(blocks) == 1:
        individual_block_plots = True
        make_full_night_plot = False
    elif individual_block_plots == False and make_full_night_plot == False:
        make_full_night_plot = True
    #make a unique plot for each unique date and reference field combination
    if individual_block_plots == True:
        for block in blocks:
            frames_all_filters = Frame.objects.filter(block = block, frametype__in=[Frame.BANZAI_RED_FRAMETYPE,])
            fig, ax = plt.subplots(nrows = 1, tight_layout = True)
            block_date_str = f"{block.block_start}"[:-9]
            for filter in filters:
                fwhms = []
                midpoints = []
                frames = frames_all_filters.filter(filter=filter)
                for frame in frames.order_by('midpoint', 'frametype'):
                    fwhms.append(frame.fwhm)
                    midpoints.append(frame.midpoint)
                current_colorcode = colors[np.where(filters==filter)[0][0]]
                ax.plot(midpoints, fwhms, color = current_colorcode, label = f'{filter}')
            ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
            field_name = block.calibsource.name[-3:]
            filename = os.path.join(output_dir, f"single_block_FWHM_plot_{block_date_str}_Field_{field_name}.png")
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            fig.suptitle(f"FWHM for {block.site} {block_date_str} Block, Field {field_name}")
            fig.legend()
            fig.savefig(filename)
            filenames.append(f"{filename}")
    #make combined plots for blocks on same night
    if make_full_night_plot == True:
        start_dates = []
        block_ids = []
        for block in blocks:
            if block.block_start not in start_dates:
                start_dates.append(block.block_start)
            block_ids.append(block.id)
        for date in start_dates:
            current_blocks = Block.objects.filter(id__in = block_ids, block_start = date)
            current_blocks = current_blocks.order_by('when_observed')
            supplot_count = 1
            subplot_count = 0
            if len(current_blocks) >= 5:
                fig, ax = plt.subplots(1, 5, constrained_layout = True)
            else:
                fig, ax = plt.subplots(1, len(current_blocks), constrained_layout = True)
            field_names = []
            for i, block in enumerate(current_blocks):
                block_date_str = f"{block.block_start}"[:-9]
                field_name = block.calibsource.name[-3:]
                field_names.append(field_name)
                field_name = block.calibsource.name[-3:]
                frames_all_filters = Frame.objects.filter(block = block, frametype__in=[Frame.BANZAI_RED_FRAMETYPE,])
                for filter in filters:
                    fwhms = []
                    midpoints = []
                    frames = frames_all_filters.filter(filter=filter)
                    for frame in frames.order_by('midpoint', 'frametype'):
                        fwhms.append(frame.fwhm)
                        midpoints.append(frame.midpoint)
                    current_colorcode = colors[np.where(filters==filter)[0][0]]
                    try:
                        if subplot_count % 5 == 0:
                            ax[i % 5].plot(midpoints, fwhms, color = current_colorcode, label = f'{filter}')
                        else:
                            ax[i % 5].plot(midpoints, fwhms, color = current_colorcode)
                        ax[i % 5].set_title(f"{field_name}", fontsize = 7)
                    except TypeError:
                        ax = [ax]
                        if subplot_count % 5 == 0:
                                ax[i % 5].plot(midpoints, fwhms, color = current_colorcode, label = f'{filter}')
                        else:
                                ax[i % 5].plot(midpoints, fwhms, color = current_colorcode)
                        ax[i % 5].set_title(f"{field_name}", fontsize = 7)
                subplot_count +=1
                if subplot_count % 5 == 0 or i == len(current_blocks) - 1:
                    ax[0].xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax[0].xaxis.get_major_locator()))
                    ax[0].tick_params(axis='x', labelsize= 5)
                    for ax_rotator in range (0, len(ax)):
                        if ax_rotator != 0:
                            ax[ax_rotator].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                            ax[ax_rotator].tick_params(axis='x', labelsize= 5)
                        plt.setp(ax[ax_rotator].get_xticklabels(), rotation=60, horizontalalignment='right')
                    fields_str_for_file = "_".join(field_names)
                    fields_str_for_title = ",".join(field_names)
                    shortfilename = f"_FWHM_plot_{block.get_blockdayobs}_Field_{fields_str_for_file}_plot{supplot_count}.png"
                    filename = os.path.join(output_dir, shortfilename)
                    filenames.append(filename)
                    os.makedirs(os.path.dirname(filename), exist_ok=True)
                    fig.suptitle(f"FWHM for {block_date_str} Block, Field # \n {fields_str_for_title}, Plot # {supplot_count}")
                    fig.legend()
                    fig.savefig(filename)
                    fig.clf()
                    if (len(current_blocks) - 5*supplot_count) >= 5:
                        fig, ax = plt.subplots(1, 5, constrained_layout = True)
                    elif 0 < (len(current_blocks) - 5*supplot_count) < 5:
                        fig, ax = plt.subplots(1, (len(current_blocks) - 5*supplot_count), constrained_layout = True)
                    else:
                        break
                    supplot_count +=1
                    field_names = []
                elif i == len(current_blocks) - 1:
                    break
                else:
                    continue
    return filenames



def plot_magnitude(block, filter, photometry_table, savepath, bad_subtractions, err_threshold_mag = None, err_threshold_zp = None, account_zps = True, aperture_radius = None):
    '''Plots light curve in the passed \<block\> for a specified \<filter\> on a single plot using a \<photometry_table\>, subplot containing fwhm and zp is added
    to better understand data and bad subtractions are labeled with a '*'. Use \<savepath\> to enter a directory for saving the plot
    Use examine_subtractions to find bad subtractions, then pass their file names as a list in \<bad_subtractions\> for labelling.
    If you would like data points with high uncertainty to be excluded, pass a value \<err_threshold_maf\> for maximum tolerable
    error in magnitude. All magnitudes with an error greater than the value will be dropped from the plot. Repeat for
    \<err_threshold_zp\> to set a maximum error for zeropoints. WARNING: Make sure aperture radius and zp account specs
    match what is in aperture photometry table, otherwise it may overwrite a plot for the same block with different specs'''
    times_col = photometry_table['times'].data
    magnitudes_col = photometry_table['mag'].data
    magnitude_errs_col = photometry_table['magerr'].data
    fwhms_col = photometry_table['FWHM'].data
    zeropoints_col = photometry_table['ZP'].data
    zeropoint_errs_col = photometry_table['ZP_sig']
    bad_zp_loc_col = list(np.where(photometry_table['ZP'].data < -90)[0])
    times_col = np.delete(times_col, bad_zp_loc_col, 0)
    frames_col = photometry_table['path to frame'].data
    frames_col = np.delete(frames_col, bad_zp_loc_col, 0)
    magnitudes_col = np.delete(magnitudes_col, bad_zp_loc_col, 0)
    magnitude_errs_col = np.delete(magnitude_errs_col, bad_zp_loc_col, 0)
    if err_threshold_mag is not None:
        mag_errs_for_deletion = []
        for i, mag_err in enumerate(magnitude_errs_col):
            if mag_err > err_threshold_mag:
                mag_errs_for_deletion.append(i)
        magnitudes_col = np.delete(magnitudes_col, mag_errs_for_deletion, 0)
        magnitude_errs_col = np.delete(magnitude_errs_col, mag_errs_for_deletion, 0)
        times_for_mags_col = np.delete(times_col, mag_errs_for_deletion, 0)
    zeropoints_col = np.delete(zeropoints_col, bad_zp_loc_col, 0)
    zeropoint_errs_col = np.delete(zeropoint_errs_col, bad_zp_loc_col, 0)
    if err_threshold_zp is not None:
        zp_errs_for_deletion = []
        for i, zp_err in enumerate(zeropoint_errs_col):
            if zp_err > err_threshold_zp:
                zp_errs_for_deletion.append(i)
        zeropoints_col = np.delete(zeropoints_col, zp_errs_for_deletion, 0)
        zeropoint_errs_col = np.delete(zeropoint_errs_col, zp_errs_for_deletion, 0)
        times_for_zps_col = np.delete(times_col, zp_errs_for_deletion, 0)
    filters_col = photometry_table['filters'].data
    fwhms = []
    times = []
    magnitudes = []
    magnitude_errs = []
    zeropoints = []
    zeropoint_errs = []
    times_for_mags = []
    times_for_zps = []
    if err_threshold_mag == None and err_threshold_zp == None:
        for i in range (0, len(times_col)):
            if filters_col[i] == filter:
                times.append(times_col[i])
                fwhms.append(fwhms_col[i])
                magnitudes.append(magnitudes_col[i])
                magnitude_errs.append(magnitude_errs_col[i])
                zeropoints.append(zeropoints_col[i])
                zeropoint_errs.append(zeropoint_errs_col[i])
    elif err_threshold_mag != None and err_threshold_zp == None:
        for i in range (0, len(times_col)):
            if filters_col[i] == filter:
                times.append(times_col[i])
                fwhms.append(fwhms_col[i])
                zeropoints.append(zeropoints_col[i])
                zeropoint_errs.append(zeropoint_errs_col[i])
        for i in range (0, len(times_for_mags_col)):
            if filters_col[i] == filter:
                times_for_mags.append(times_for_mags_col[i])
                magnitudes.append(magnitudes_col[i])
                magnitude_errs.append(magnitude_errs_col[i])
    elif err_threshold_zp != None and err_threshold_mag == None:
        for i in range (0, len(times_col)):
            if filters_col[i] == filter:
                times.append(times_col[i])
                fwhms.append(fwhms_col[i])
                magnitudes.append(magnitudes_col[i])
                magnitude_errs.append(magnitude_errs_col[i])
        for i in range (0, len(times_for_zps_col)):
            if filters_col[i] == filter:
                times_for_zps.append(times_for_zps_col[i])
                zeropoints.append(zeropoints_col[i])
                zeropoint_errs.append(zeropoint_errs_col[i])
    elif err_threshold_zp != None and err_threshold_mag != None:
        for i in range (0, len(times_col)):
            if filters_col[i] == filter:
                times.append(times_col[i])
                fwhms.append(fwhms_col[i])
        for i in range (0, len(times_for_zps_col)):
            if filters_col[i] == filter:
                times_for_zps.append(times_for_zps_col[i])
                zeropoints.append(zeropoints_col[i])
                zeropoint_errs.append(zeropoint_errs_col[i])
        for i in range (0, len(times_for_mags_col)):
            if filters_col[i] == filter:
                times_for_mags.append(times_for_mags_col[i])
                magnitudes.append(magnitudes_col[i])
                magnitude_errs.append(magnitude_errs_col[i])
    if len(times) == 0:
        return 'no data for selected filter'
    bad_sub_x_axis = []
    bad_sub_y_axis = []
    if bad_subtractions != None:
        for bad_subtract in bad_subtractions:
            bad_frame = Frame.objects.filter(filename = bad_subtract)[0]
            bad_sub_x_axis.append(bad_frame.midpoint)
            bad_sub_y_axis.append(np.max(magnitudes))
    fig, (ax0, ax1) = plt.subplots(nrows=2, sharex=True, gridspec_kw={'height_ratios': [15, 4]})
    block_date_str = f"{block.block_start}"[:-9]
    ax0.invert_yaxis()
    ax1.invert_yaxis()
    if err_threshold_mag == None and err_threshold_zp == None:
        ax0.errorbar(times, magnitudes, linestyle = '', ecolor = 'black', marker = 'o', markersize = 4, markerfacecolor = 'black', markeredgecolor = 'black', yerr = magnitude_errs, label = f'mag')
        ax1.errorbar(times, zeropoints, linestyle = '', ecolor = 'red', marker = 'o', markersize = 4, markerfacecolor = 'red', markeredgecolor = 'red', yerr = zeropoint_errs, label = f'zp')
    elif err_threshold_mag != None and err_threshold_zp == None:
        ax0.errorbar(times_for_mags, magnitudes, linestyle = '', ecolor = 'black', marker = 'o', markersize = 4, markerfacecolor = 'black', markeredgecolor = 'black', yerr = magnitude_errs, label = f'mag')
        ax1.errorbar(times, zeropoints, linestyle = '', ecolor = 'red', marker = 'o', markersize = 4, markerfacecolor = 'red', markeredgecolor = 'red', yerr = zeropoint_errs, label = f'zp')
    elif err_threshold_zp != None and err_threshold_mag == None:
        ax0.errorbar(times, magnitudes, linestyle = '', ecolor = 'black', marker = 'o', markersize = 4, markerfacecolor = 'black', markeredgecolor = 'black', yerr = magnitude_errs, label = f'mag')
        ax1.errorbar(times_for_zps, zeropoints, linestyle = '', ecolor = 'red', marker = 'o', markersize = 4, markerfacecolor = 'red', markeredgecolor = 'red', yerr = zeropoint_errs, label = f'zp')
    elif err_threshold_zp != None and err_threshold_mag != None:
        ax0.errorbar(times_for_mags, magnitudes, linestyle = '', ecolor = 'black', marker = 'o', markersize = 4, markerfacecolor = 'black', markeredgecolor = 'black', yerr = magnitude_errs, label = f'mag')
        ax1.errorbar(times_for_zps, zeropoints, linestyle = '', ecolor = 'red', marker = 'o', markersize = 4, markerfacecolor = 'red', markeredgecolor = 'red', yerr = zeropoint_errs, label = f'zp')
    ax2 = ax1.twinx()
    ax2.scatter(times, fwhms, color= '#73BF69', s = 25, alpha = 0.5)
    ax2.set_ylabel('FWHM (")')
    ax0.xaxis.set_minor_locator(AutoMinorLocator())
    ax1.xaxis.set_minor_locator(AutoMinorLocator())
    for i in range(0, len(bad_sub_x_axis)):
        ax0.text(x = bad_sub_x_axis[i], y = bad_sub_y_axis[i], s = '*')
        ax1.text(x = bad_sub_x_axis[i], y = bad_sub_y_axis[i], s = '*')
    ax1.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax0.xaxis.get_major_locator()))
    ax0.legend()
    ax1.legend()
    if aperture_radius == None:
        aper_rad_label = '2.5*fwhm'
    else:
        aper_rad_label = aperture_radius
    if account_zps == True:
        if err_threshold_mag == None and err_threshold_zp == None:
            filename = os.path.join(savepath, f"{filter}_magnitude_plot_{block_date_str}_Block_aper_radius_{aper_rad_label}_zps_included.png")
            fig.suptitle(f"{filter} Magnitude Light Curve for {block.site} {block_date_str} Block")
            fig.savefig(filename)
        elif err_threshold_mag != None and err_threshold_zp == None:
            filename = os.path.join(savepath, f"{filter}_magnitude_plot_{block_date_str}_Block_magerr_thresh_{err_threshold_mag}_aper_radius_{aper_rad_label}_zps_included.png")
            fig.suptitle(f"{filter} Magnitude Light Curve for {block.site} {block_date_str} Block \n Magnitude Error Thresh = {err_threshold_mag}")
            fig.savefig(filename)
        elif err_threshold_zp != None and err_threshold_mag == None:
            filename = os.path.join(savepath, f"{filter}_magnitude_plot_{block_date_str}_Block_zperr_thresh_{err_threshold_zp}_aper_radius_{aper_rad_label}_zps_included.png")
            fig.suptitle(f"{filter} Magnitude Light Curve for {block.site} {block_date_str} Block \n ZP Error Thresh = {err_threshold_zp}")
            fig.savefig(filename)
        elif err_threshold_zp != None and err_threshold_mag != None:
            filename = os.path.join(savepath, f"{filter}_magnitude_plot_{block_date_str}_Block_magerr_thresh_{err_threshold_mag}_aper_radius_{aper_rad_label}_zps_included.png")
            fig.suptitle(f"{filter} Magnitude Light Curve for {block.site} {block_date_str} Block \n Magnitude Error Thresh = {err_threshold_mag} \n ZP Error Thresh = {err_threshold_zp}")
            fig.savefig(filename)
    if account_zps == False:
        if err_threshold_mag == None and err_threshold_zp == None:
            filename = os.path.join(savepath, f"{filter}_magnitude_plot_{block_date_str}_Block_aper_radius_{aper_rad_label}_zps_excluded.png")
            fig.suptitle(f"{filter} Magnitude Light Curve for {block.site} {block_date_str} Block")
            fig.savefig(filename)
        elif err_threshold_mag != None and err_threshold_zp == None:
            filename = os.path.join(savepath, f"{filter}_magnitude_plot_{block_date_str}_Block_magerr_thresh_{err_threshold_mag}_aper_radius_{aper_rad_label}_zps_excluded.png")
            fig.suptitle(f"{filter} Magnitude Light Curve for {block.site} {block_date_str} Block \n Magnitude Error Thresh = {err_threshold_mag}")
            fig.savefig(filename)
        elif err_threshold_zp != None and err_threshold_mag == None:
            filename = os.path.join(savepath, f"{filter}_magnitude_plot_{block_date_str}_Block_zperr_thresh_{err_threshold_zp}_aper_radius_{aper_rad_label}_zps_excluded.png")
            fig.suptitle(f"{filter} Magnitude Light Curve for {block.site} {block_date_str} Block \n ZP Error Thresh = {err_threshold_zp}")
            fig.savefig(filename)
        elif err_threshold_zp != None and err_threshold_mag != None:
            filename = os.path.join(savepath, f"{filter}_magnitude_plot_{block_date_str}_Block_magerr_thresh_{err_threshold_mag}_aper_radius_{aper_rad_label}_zps_excluded.png")
            fig.suptitle(f"{filter} Magnitude Light Curve for {block.site} {block_date_str} Block \n Magnitude Error Thresh = {err_threshold_mag} \n ZP Error Thresh = {err_threshold_zp}")
            fig.savefig(filename)
    fig.clf()
    return filename

def generalized_zeropoint_plotter(blocks_or_ref_fields, filters, colors, output_dir, individual_block_plots, make_full_night_plot):
    """Plots zeropoints against time for each filter in a block or group of blocks over the blocks' observation nights.
    Pass a block, list/Queryset of blocks, reference field, or list/Queryset of reference fields through \<blocks_or_ref_fields\>.
    If a single block is passed, it will be thrown into a one element list. If a list or Queryset of blocks is passed, all elements
    will be thrown into a new list. If a reference field is passed, function will find all blocks in the reference field and throw them
    into a list. The same process will be done for a list of reference fields; all reference will be looped over and have their blocks
    extracted + thrown into the same list. No matter which of the four options is passed, it will be configured into a list of blocks.
    Pass a list of \<filters\> for which to plot zeropoint, and a corresponding list of colors for which the color matches the filter at its
    same index. This determines the color coding and legends for the plot. Select an \<output_dir\> as an output directory to save the
    figure(s). Finally, select True or False for \<individual_block_plots\> and \<make_full_night_plot\>. If \<individual_block_plots\>
    is true, an individual plot of zeropoints for all filters will be made for each block (unique date + ref field combo). If <\make_full
    _night_plot\> is True, it will make a plot for a night of observation; if multiple blocks fall on this night they will appear as
    subplots labelled by their corresponding reference field. If there are more than 5 blocks sharing a night of observation, multiple
    plots will be made for the night, each with 5 subplots in chronological order representing each block. If #blocks % 5 != 0, the final
    plot will contain as many subplots as there are blocks in the remainder. The separate plots will be numbered in chronological order,
    (i.e. first 5 blocks chronologically = plot 1, second 5 blocks= plot 2, ...). If \<individual_block_plots\> and \<make_full_night_plot\>
    are True, both actions will be executed. If both are false, function defaults to \<make_full_night_plot\> = True. If there is only one block,
    \<individual_block_plots\> defaults to true and \<make_full_night_plot\> defaults to false to save computational time, since for one block
    they do the same thing and individual block plots are faster. """
    filenames = []
    if type(filters) != np.ndarray:
        filters = np.array(filters)
    if type(colors) != np.ndarray:
        colors = np.array(colors)
    #determine datatype given and extract corresponding blocks
    try:
        blocks = []
        if isinstance(blocks_or_ref_fields[0], core.models.sources.StaticSource) == True:
            ref_fields = blocks_or_ref_fields
            for ref_field in ref_fields:
                from_statsource_get_blocks = Block.objects.filter(superblock__calibsource = ref_field).order_by('block_start')
                obs_blocks = from_statsource_get_blocks.filter(num_observed__gte=1)
                for item in obs_blocks:
                    blocks.append(item)
        elif isinstance(blocks_or_ref_fields[0], core.models.blocks.Block) == True:
            blockset = blocks_or_ref_fields
            for item in blockset:
                blocks.append(item)
    except TypeError:
        if isinstance(blocks_or_ref_fields, core.models.blocks.Block) == True:
            blocks = [blocks_or_ref_fields]
        elif isinstance(blocks_or_ref_fields, core.models.sources.StaticSource) == True:
            blocks = []
            from_statsource_get_blocks = Block.objects.filter(calibsource = blocks_or_ref_fields).order_by('block_start')
            obs_blocks = from_statsource_get_blocks.filter(num_observed__gte=1)
            for item in obs_blocks:
                blocks.append(item)
    if len(blocks) == 1:
        individual_block_plots = True
        make_full_night_plot = False
    elif individual_block_plots == False and make_full_night_plot == False:
        make_full_night_plot = True
    #make a unique plot for each unique date and reference field combination
    if individual_block_plots == True:
        for block in blocks:
            frames_all_filters = Frame.objects.filter(block = block, frametype__in=[Frame.NEOX_RED_FRAMETYPE])
            fig, ax = plt.subplots(nrows = 1, tight_layout = True)
            block_date_str = f"{block.block_start}"[:-9]
            for filter in filters:
                zeropoints = []
                midpoints = []
                frames = frames_all_filters.filter(filter=filter)
                for frame in frames.order_by('midpoint', 'frametype'):
                    try:
                        if frame.zeropoint > 0:
                            zeropoints.append(frame.zeropoint)
                            midpoints.append(frame.midpoint)
                    except TypeError:
                        pass
                current_colorcode = colors[np.where(filters==filter)[0][0]]
                ax.plot(midpoints, zeropoints, color = current_colorcode, label = f'{filter}')
            ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
            field_name = block.calibsource.name[-3:]
            filename = os.path.join(output_dir, f"single_block_ZP_plot_{block_date_str}_Field_{field_name}.png")
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            fig.suptitle(f"Zero Points for {block.site} {block_date_str} Block, Field {field_name}")
            fig.legend()
            fig.savefig(filename)
            filenames.append(f"{filename}")
    #make combined plots for blocks on same night
    if make_full_night_plot == True:
        start_dates = []
        block_ids = []
        for block in blocks:
            if block.block_start not in start_dates:
                start_dates.append(block.block_start)
            block_ids.append(block.id)
        for date in start_dates:
            current_blocks = Block.objects.filter(id__in = block_ids, block_start = date)
            current_blocks = current_blocks.order_by('when_observed')
            supplot_count = 1
            subplot_count = 0
            if len(current_blocks) >= 5:
                fig, ax = plt.subplots(1, 5, constrained_layout = True)
            else:
                fig, ax = plt.subplots(1, len(current_blocks), constrained_layout = True)
            field_names = []
            for i, block in enumerate(current_blocks):
                block_date_str = f"{block.block_start}"[:-9]
                field_name = block.calibsource.name[-3:]
                field_names.append(field_name)
                field_name = block.calibsource.name[-3:]
                frames_all_filters = Frame.objects.filter(block = block, frametype__in=[Frame.NEOX_RED_FRAMETYPE])
                for filter in filters:
                    zeropoints = []
                    midpoints = []
                    frames = frames_all_filters.filter(filter=filter)
                    for frame in frames.order_by('midpoint', 'frametype'):
                        try:
                            if frame.zeropoint > 0:
                                zeropoints.append(frame.zeropoint)
                                midpoints.append(frame.midpoint)
                        except TypeError:
                            pass
                    current_colorcode = colors[np.where(filters==filter)[0][0]]
                    try:
                        if subplot_count % 5 == 0:
                            ax[i % 5].plot(midpoints, zeropoints, color = current_colorcode, label = f'{filter}')
                        else:
                            ax[i % 5].plot(midpoints, zeropoints, color = current_colorcode)
                        ax[i % 5].set_title(f"{field_name}", fontsize = 7)
                    except TypeError:
                        ax = [ax]
                        if subplot_count % 5 == 0:
                                ax[i % 5].plot(midpoints, zeropoints, color = current_colorcode, label = f'{filter}')
                        else:
                                ax[i % 5].plot(midpoints, zeropoints, color = current_colorcode)
                        ax[i % 5].set_title(f"{field_name}", fontsize = 7)
                subplot_count +=1
                if subplot_count % 5 == 0 or i == len(current_blocks) - 1:
                    ax[0].xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax[0].xaxis.get_major_locator()))
                    ax[0].tick_params(axis='x', labelsize= 5)
                    for ax_rotator in range (0, len(ax)):
                        if ax_rotator != 0:
                            ax[ax_rotator].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                            ax[ax_rotator].tick_params(axis='x', labelsize= 5)
                        plt.setp(ax[ax_rotator].get_xticklabels(), rotation=60, horizontalalignment='right')
                    fields_str_for_file = "_".join(field_names)
                    fields_str_for_title = ",".join(field_names)
                    shortfilename = f"_ZP_plot_{block.get_blockdayobs}_Field_{fields_str_for_file}_plot{supplot_count}.png"
                    filename = os.path.join(output_dir, shortfilename)
                    filenames.append(filename)
                    os.makedirs(os.path.dirname(filename), exist_ok=True)
                    fig.suptitle(f"Zero Points for {block_date_str} Block, Field # \n {fields_str_for_title}, Plot # {supplot_count}")
                    fig.legend()
                    fig.savefig(filename)
                    fig.clf()
                    if (len(current_blocks) - 5*supplot_count) >= 5:
                        fig, ax = plt.subplots(1, 5, constrained_layout = True)
                    elif 0 < (len(current_blocks) - 5*supplot_count) < 5:
                        fig, ax = plt.subplots(1, (len(current_blocks) - 5*supplot_count), constrained_layout = True)
                    else:
                        break
                    supplot_count +=1
                    field_names = []
                elif i == len(current_blocks) - 1:
                    break
                else:
                    continue
    return filenames
