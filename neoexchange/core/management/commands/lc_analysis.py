"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2016-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

Prepare LC to be analysed with DAMIT
"""

import os
from glob import glob
from datetime import datetime, timedelta, time
from math import floor, log10
import numpy as np

from django.core.management.base import BaseCommand, CommandError
from django.core.files.storage import default_storage
from django.db.models import Q
from django.conf import settings

import matplotlib.pyplot as plt
from matplotlib.dates import HourLocator, DateFormatter
from astropy.stats import LombScargle
import astropy.units as u
from astropy.time import Time

from core.views import import_alcdef
from core.models import Body, model_to_dict, DataProduct
from core.utils import search, save_dataproduct
from astrometrics.time_subs import jd_utc2datetime, datetime2mjd_utc
from astrometrics.ephem_subs import compute_ephem
from photometrics.catalog_subs import sanitize_object_name
from photometrics.external_codes import run_damit_periodscan, run_damit


class Command(BaseCommand):

    help = 'Convert ALCDEF into format DAMIT can use and run DAMIT.'

    def add_arguments(self, parser):
        out_path = settings.DATA_ROOT
        parser.add_argument('body', type=str, help='Object name (use underscores instead of spaces)')
        parser.add_argument('-pmin', '--period_min', type=float, default=None, help='min period for period search (h)')
        parser.add_argument('-pmax', '--period_max', type=float, default=None, help='max period for period search (h)')
        parser.add_argument('-p', '--period', type=float, default=None, help='base period to search around (h)')
        parser.add_argument('--filters', type=str, default=None, help='comma separated list of filters to use (SG,SR,W)')
        parser.add_argument('--period_scan', action="store_true", default=False, help='run Period Scan')
        parser.add_argument('--lc_model', action="store", default=None, help='Start and end dates for the lc_model (YYYYMMDD-YYYMMDD)')
        parser.add_argument('--path', type=str, default=out_path, help='Location for local DAMIT data to live')
        parser.add_argument('--ext_alcdef', type=str, default=None, help='path/filename for external alcdef data to be uploaded')

    def get_period_range(self, body, options):
        """
        Calculate period range to search from optional input parameters and known period
        :param body: Body object
        :param options: input options
        :return: pmin, pmax, period
        """
        pmin = options['period_min']
        pmax = options['period_max']
        period = options['period']
        if period is None or period <= 0:
            best_period = body.get_physical_parameters('P', False)
            if best_period:
                period = best_period[0].get('value', None)
            else:
                period = None
        if (pmin is None or pmin <= 0) and (pmax is None or pmax <= 0):
            if period is None:
                period = 1
            pmin = period - 0.5
            pmax = period + 0.5
        elif pmin and (pmax is None or pmax <= 0):
            pmax = pmin + 1
        elif pmin is None and pmax:
            pmin = pmax - 1
        if pmin <= 0:
            pmin = .5 * pmax
        return pmin, pmax, period

    def astro_centric_coord(self, geocent_a, heliocent_e):
        astrocent_e = [-1*x for x in geocent_a]
        geocent_h = [-1*x for x in heliocent_e]
        astrocent_h = [x_g - x_a for x_g, x_a in zip(geocent_h, geocent_a)]
        return astrocent_e, astrocent_h

    def create_lcs_input(self, input_file, meta_list, lc_list, body_elements, filt_name):
        """
        Create input lcs:
        :input:
        :return:
        JD (Light-time corrected)
        Brightness (intensity)
        XYZ coordinates of Sun (astrocentric cartesian coordinates) AU
        XYZ coordinates of Earth (astrocentric cartesian coordinates) AU
        """
        input_file.write(f"{len([x for x in meta_list if x['FILTER'] in filt_name])}\n")
        mag_mean_list = []
        ltt_list = []
        for k, dat in enumerate(meta_list):
            site = dat['MPCCODE']
            mean_mag = np.mean(lc_list[k]['mags'])
            mag_mean_list.append({'mean_mag': mean_mag, 'num_dates': len(lc_list[k]['mags'])})
            mean_intensity = 10 ** (0.4 * mean_mag)
            if dat['FILTER'] in filt_name:
                input_file.write(f"{len(lc_list[k]['mags'])} 0\n")
                for c, d in enumerate(lc_list[k]['date']):
                    ephem_date = jd_utc2datetime(d)
                    ephem = compute_ephem(ephem_date, body_elements, site)
                    astrocent_e, astrocent_h = self.astro_centric_coord(ephem["geocnt_a_pos"], ephem["heliocnt_e_pos"])
                    d = d - ephem['ltt']/60/60/24
                    intensity = 10 ** (0.4 * lc_list[k]['mags'][c])
                    rel_intensity = intensity / mean_intensity
                    input_file.write(f"{d:.6f}   {rel_intensity:1.6E}   {astrocent_e[0]:.6E} {astrocent_e[1]:.6E}"
                                     f" {astrocent_e[2]:.6E}   {astrocent_h[0]:.6E} {astrocent_h[1]:.6E}"
                                     f" {astrocent_h[2]:.6E}\n")
                    ltt_list.append(ephem['ltt']/60/60/24)
        return mag_mean_list, ltt_list

    def create_epoch_input(self, epoch_file, period, start_date, end_date, body_elements):
        # step_size = period * 60 * 60 / 10
        # epoch_length = end_date - start_date
        # total_steps = epoch_length.total_seconds() / step_size
        total_steps = 1000
        epoch_length = end_date - start_date
        step_size = epoch_length.total_seconds() / 500
        epoch_list = [start_date + timedelta(seconds=step_size*x) for x in range(round(total_steps))]
        rel_intensity = 1.0
        epoch_file.write(f"1\n")
        epoch_file.write(f"{len(epoch_list)} 0\n")
        mag_list = []
        ltt_list = []
        for d in epoch_list:
            jd = datetime2mjd_utc(d)+2400000.5
            ephem = compute_ephem(d, body_elements, '500')
            astrocent_e, astrocent_h = self.astro_centric_coord(ephem["geocnt_a_pos"], ephem["heliocnt_e_pos"])
            jd = jd - ephem['ltt']/60/60/24
            epoch_file.write(f"{jd:.6f}   {rel_intensity:1.6E}   {astrocent_e[0]:.6E} {astrocent_e[1]:.6E}"
                             f" {astrocent_e[2]:.6E}   {astrocent_h[0]:.6E} {astrocent_h[1]:.6E}"
                             f" {astrocent_h[2]:.6E}\n")
            mag_list.append(ephem['mag'])
            ltt_list.append(ephem['ltt']/60/60/24)

        return np.mean(mag_list), ltt_list

    def import_or_create_psinput(self, path, obj_name, pmin, pmax):
        """
        If input_period_scan file exists, update period range, else create file from scratch
        :param path: path to working directory
        :param obj_name: sanitized object name
        :param pmin: minimum period
        :param pmax: maximum period
        :return: filename for input_period_scan
        """
        base_name = obj_name + '_period_scan.in'
        ps_input_filename = os.path.join(path, base_name)
        ps_input_file = open(ps_input_filename, 'w+')
        lines = ps_input_file.readlines()
        if lines:
            lines[0] = f"{pmin} {pmax} 0.8	period start - end - interval coeff.\n"
            for line in lines:
                ps_input_file.write(line)
        else:
            ps_input_file.write(f"{pmin} {pmax} 0.8	period start - end - interval coeff.\n")
            ps_input_file.write(f"0.1			convexity weight\n")
            ps_input_file.write(f"6 6			degree and order of spherical harmonics\n")
            ps_input_file.write(f"8			no. of rows\n")
            ps_input_file.write(f"0.5	0		scattering parameters\n")
            ps_input_file.write(f"0.1	0\n")
            ps_input_file.write(f"-0.5	0\n")
            ps_input_file.write(f"0.1	0\n")
            ps_input_file.write(f"50	  		iteration stop condition\n")
            ps_input_file.write(f"10			minimum number of iterations (only if the above value < 1)\n")
        ps_input_file.close()
        return ps_input_filename

    def import_or_create_cinv_input(self, path, obj_name, period):
        """
        If input_period_scan file exists, update period range, else create file from scratch
        Create conjgradinv file if one doesn't exist
        :param path: path to working directory
        :param obj_name: sanitized object name
        :param period: best period
        :return: filenames for inversion programs
        """
        base_name = obj_name + '_convex_inv.in'
        cinv_input_filename = os.path.join(path, base_name)
        try:
            cinv_input_file = open(cinv_input_filename, 'r+')
        except FileNotFoundError:
            cinv_input_file = open(cinv_input_filename, 'w+')
        lines = cinv_input_file.readlines()
        print(lines)
        if lines and len(lines) == 13:
            lines[2] = f"{period}		1	inital period [hours] (0/1 - fixed/free)\n"
            for line in lines:
                cinv_input_file.write(line)
        else:
            cinv_input_file.write(f"220		1	inital lambda [deg] (0/1 - fixed/free)\n")
            cinv_input_file.write(f"0		1	initial beta [deg] (0/1 - fixed/free)\n")
            cinv_input_file.write(f"{period}		1	inital period [hours] (0/1 - fixed/free)\n")
            cinv_input_file.write(f"0			zero time [JD]\n")
            cinv_input_file.write(f"0			initial rotation angle [deg]\n")
            cinv_input_file.write(f"1.0			convexity regularization\n")
            cinv_input_file.write(f"6 6			degree and order of spherical harmonics expansion\n")
            cinv_input_file.write(f"8			number of rows\n")
            cinv_input_file.write(f"0.5		0	phase funct. param. 'a' (0/1 - fixed/free)\n")
            cinv_input_file.write(f"0.1		0	phase funct. param. 'd' (0/1 - fixed/free)\n")
            cinv_input_file.write(f"-0.5		0	phase funct. param. 'k' (0/1 - fixed/free)\n")
            cinv_input_file.write(f"0.1		0	Lambert coefficient 'c' (0/1 - fixed/free)\n")
            cinv_input_file.write(f"50			iteration stop condition\n")
        cinv_input_file.close()

        base_conjgrad_name = obj_name + '_conjgrad_inv.in'
        conj_input_filename = os.path.join(path, base_conjgrad_name)
        conj_input_file = open(conj_input_filename, 'w+')
        lines = conj_input_file.readlines()
        if not lines:
            conj_input_file.write("0.2			convexity weight\n")
            conj_input_file.write("8			number of rows\n")
            conj_input_file.write("100			number of iterations\n")
        conj_input_file.close()

        return cinv_input_filename, conj_input_filename

    def zip_lc_model(self, epoch_in, lc_in, lc_out, mag_means=None, ltt_list=None):
        epoch_in_file = open(epoch_in, 'r')
        lc_in_file = open(lc_in, 'r')
        lc_out_file = open(lc_out, 'w+')
        epoch_lines = epoch_in_file.readlines()
        lc_lines = iter(lc_in_file.readlines())
        i = -1
        k = 0
        for dline in epoch_lines:
            chunks = dline.split()
            if len(chunks) > 3:
                if mag_means:
                    if isinstance(mag_means, list):
                        mean_mag = mag_means[i]['mean_mag']
                    else:
                        mean_mag = mag_means
                else:
                    mean_mag = 0
                mag = log10(float(next(lc_lines).rstrip())) / 0.4 + mean_mag
                if ltt_list:
                    jd = float(chunks[0]) + ltt_list[k]
                else:
                    jd = chunks[0]
                lc_out_file.write(f"{jd} {mag}\n")
                k += 1
            elif len(chunks) > 1:
                lc_out_file.write(f"{chunks[0]}\n")
                i += 1
        epoch_in_file.close()
        lc_in_file.close()
        lc_out_file.close()

    def handle(self, *args, **options):
        body_name = options['body']
        body_name = body_name.replace('_', ' ')
        object_list = []
        if body_name.isdigit():
            object_list = Body.objects.filter(Q(designations__value=body_name) | Q(name=body_name))
        if not object_list and not (body_name.isdigit() and int(body_name) < 2100):
            object_list = Body.objects.filter(Q(designations__value__iexact=body_name) | Q(provisional_name=body_name) | Q(provisional_packed=body_name) | Q(name=body_name))
        try:
            body = object_list[0]
        except IndexError:
            print(f"Couldn't find {body_name}")
            return
        if options['ext_alcdef'] is not None:
            save_dataproduct(obj=body, filepath=options['ext_alcdef'], filetype=DataProduct.ALCDEF_TXT)
        alcdef_files = DataProduct.content.fullbody(bodyid=body.id).filter(filetype=DataProduct.ALCDEF_TXT)
        meta_list = []
        lc_list = []
        for alcdef in alcdef_files:
            meta_list, lc_list = import_alcdef(alcdef.product.file, meta_list, lc_list)
        body_elements = model_to_dict(body)
        obj_name = sanitize_object_name(body.current_name())

        if options['filters']:
            filt_list = options['filters'].upper()
        else:
            filt_list = list(set([meta['FILTER'] for meta in meta_list]))
        # Create lightcurve input file
        path = os.path.join(options['path'], 'Reduction', obj_name)
        lcs_input_filename = os.path.join(path, obj_name + '_input.lcs')
        lcs_input_file = open(lcs_input_filename, 'w')
        mag_means, lc_ltt_list = self.create_lcs_input(lcs_input_file, meta_list, lc_list, body_elements, filt_list)
        lcs_input_file.close()
        pmin, pmax, period = self.get_period_range(body, options)
        dir_num = 0
        dirs = [item for item in os.listdir(path) if 'DamitDocs' in item]
        if dirs:
            for d in dirs:
                d_num = int(d.split('_')[1])
                if dir_num < d_num:
                    dir_num = d_num
        if options['period_scan']:
            # Create period_scan input file
            psinput_filename = self.import_or_create_psinput(path, obj_name, pmin, pmax)
            # Run Period Scan
            psoutput_filename = os.path.join(path, f'{obj_name}_{pmin}T{pmax}_period_scan.out')
            ps_retcode_or_cmdline = run_damit_periodscan(lcs_input_filename, psinput_filename, psoutput_filename)
            save_dataproduct(obj=body, filepath=psoutput_filename, filetype=DataProduct.PERIODOGRAM_RAW)
        elif options['lc_model']:
            if isinstance(options['lc_model'], str):
                try:
                    start_stop_dates = options['lc_model'].split('-')
                    start_date = datetime.strptime(start_stop_dates[0], '%Y%m%d')
                    end_date = datetime.strptime(start_stop_dates[1], '%Y%m%d')
                except ValueError:
                    raise CommandError(usage)
            else:
                start_date = options['lc_model'][0]
                end_date = options['lc_model'][1]
            epoch_input_filename = os.path.join(path, obj_name + '_epoch.lcs')
            epoch_input_file = open(epoch_input_filename, 'w')
            jpl_mean_mag, model_ltt_list = self.create_epoch_input(epoch_input_file, period, start_date, end_date, body_elements)
            epoch_input_file.close()
            # Create Model lc for given epochs.
            convinv_outpar_filename = search(path, '.*.convinv_par.out', latest=True)
            shape_model_filename = search(path, '.*.trifaces.shape', latest=True)
            if not convinv_outpar_filename or not shape_model_filename:
                raise CommandError("Both convinv_par.out and model.shape files required for lc_model.")
            lcgen_outlcs_filename = os.path.join(path, obj_name + f'_{options["lc_model"]}_lcgen_lcs.out')
            lcgen_lc_final_filename = os.path.join(path, obj_name + f'_{options["lc_model"]}_lcgen_lcs.final')
            lcgenerat_retcode_or_cmdline = run_damit('lcgenerator', epoch_input_filename,
                                                     f" {convinv_outpar_filename} {shape_model_filename} {lcgen_outlcs_filename}")
            self.zip_lc_model(epoch_input_filename, lcgen_outlcs_filename, lcgen_lc_final_filename, jpl_mean_mag,
                              model_ltt_list)
        else:
            # Create convinv input file
            dir_name = os.path.join(path, f"DamitDocs_{str(dir_num + 1).zfill(3)}_{period}_{len(meta_list)}")
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
            convinv_input_filename, conjinv_input_filename = self.import_or_create_cinv_input(dir_name, obj_name, period)
            basename = os.path.join(dir_name, f'{obj_name}_{period}')
            convinv_outpar_filename = basename + '_convinv_par.out'
            convinv_outlcs_filename = basename + '_convinv_lcs.out'
            convinv_lc_final_filename = basename + '_convinv_lcs.final'
            conjinv_outareas_filename = basename + '_conjinv_areas.out'
            conjinv_outlcs_filename = basename + '_conjinv_lcs.out'
            conjinv_lc_final_filename = basename + '_conjinv_lcs.final'
            mink_faces_filename = basename + '_model.shape'
            shape_model_filename = basename + '_trifaces.shape'

            # Invert LC and calculate orientation/rotation parameters
            convexinv_retcode_or_cmdline = run_damit('convexinv', lcs_input_filename,
                                                     f"-s -p {convinv_outpar_filename} {convinv_input_filename} {convinv_outlcs_filename}")
            self.zip_lc_model(lcs_input_filename, convinv_outlcs_filename, convinv_lc_final_filename, mag_means, lc_ltt_list)

            # Refine output faces
            conjgdinv_retcode_or_cmdline = run_damit('conjgradinv', lcs_input_filename,
                                                     f"-s -o {conjinv_outareas_filename} {conjinv_input_filename} {convinv_outpar_filename} {conjinv_outlcs_filename}")
            self.zip_lc_model(lcs_input_filename, conjinv_outlcs_filename, conjinv_lc_final_filename, mag_means, lc_ltt_list)

            # Calculate polygon faces for shape
            mink_face_file = open(mink_faces_filename, 'w+')
            minkowski_retcode_or_cmdline = run_damit('minkowski', conjinv_outareas_filename, f"", write_out=mink_face_file)
            mink_face_file.close()
            # Convert faces into triangles
            shape_model_file = open(shape_model_filename, 'w+')
            stanrdtri_retcode_or_cmdline = run_damit('standardtri', mink_faces_filename, f"", write_out=shape_model_file)
            shape_model_file.close()

            # Create Data Products
            save_dataproduct(obj=body, filepath=convinv_lc_final_filename, filetype=DataProduct.MODEL_LC_RAW)
            save_dataproduct(obj=body, filepath=conjinv_lc_final_filename, filetype=DataProduct.MODEL_LC_RAW)
            save_dataproduct(obj=body, filepath=convinv_outpar_filename, filetype=DataProduct.MODEL_LC_PARAM)
            save_dataproduct(obj=body, filepath=mink_faces_filename, filetype=DataProduct.MODEL_SHAPE)

        return
