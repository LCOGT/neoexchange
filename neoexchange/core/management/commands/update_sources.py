"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2017-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.forms.models import model_to_dict
from math import degrees
from bs4 import BeautifulSoup
import logging
from astrometrics.sources_subs import random_delay, fetch_mpcobs, packed_to_normal, parse_mpcobs, PackedError
from core.models import Body, Frame, SourceMeasurement
from core.views import get_characterization_targets
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update sources to include astrometric catalog. Use no arguments to update all Characterization Targets'

    def add_arguments(self, parser):
        parser.add_argument('target', type=str, nargs='?', default=None, help='Target to update (enter Provisional Designations w/ an underscore, i.e. 2002_DF3)')

    def handle(self, *args, **options):
        if options['target']:
            obj_id = str(options['target']).replace('_', ' ')
            bodies = Body.objects.filter(name=obj_id)
        else:
            bodies = get_characterization_targets()
        i = f = 0
        for body in bodies:
            self.stdout.write("{} ==== Updating {} ==== ({} of {}) ".format(datetime.now().strftime('%Y-%m-%d %H:%M'), body.current_name(), i+1, len(bodies)))

            # measures = SourceMeasurement.objects.filter(body=body)
            # for measure in measures:
            #     print(measure.astrometric_catalog)
            # Get new observations from MPC
            obslines = self.get_mpc_obs(body.current_name())
            if obslines:
                measures = self.update_source_measurements(obslines)

            # add random 10-20s delay to keep MPC happy
            if len(bodies) > 1:
                random_delay()
            i += 1
        self.stdout.write("{} ==== Updating Complete: {} of {} Objects Updated ====".format(datetime.now().strftime('%Y-%m-%d %H:%M'), f, i))

    def get_mpc_obs(self, obj_id_or_page):
        """
        Performs remote look up of observations for object with id obj_id_or_page,
        Gets or creates corresponding Body instance and updates or creates
        SourceMeasurements.
        Alternatively obj_id_or_page can be a BeautifulSoup object, in which case
        the call to fetch_mpcdb_page() will be skipped and the passed BeautifulSoup
        object will parsed.
        """
        obj_id = None
        if type(obj_id_or_page) != BeautifulSoup:
            obj_id = obj_id_or_page
            obslines = fetch_mpcobs(obj_id)

            if obslines is None:
                logger.warning("Could not find observations for %s" % obj_id)
                return False
        else:
            page = obj_id_or_page
            obslines = page.text.split('\n')

        return obslines

    def update_source_measurements(self, obs_lines):
        # initialize measures/obs_lines
        measures = []
        if type(obs_lines) != list:
            obs_lines = [obs_lines, ]

        # find an obs_body for the mpc data
        obs_body = None
        for obs_line in reversed(obs_lines):
            param = parse_mpcobs(obs_line)
            if param:
                # Try to unpack the name first
                try:
                    try:
                        unpacked_name = packed_to_normal(param['body'])
                    except PackedError:
                        try:
                            unpacked_name = str(int(param['body']))
                        except ValueError:
                            unpacked_name = 'ZZZZZZ'
                    obs_body = Body.objects.get(Q(provisional_name__startswith=param['body']) |
                                                Q(name=param['body']) |
                                                Q(name=unpacked_name) |
                                                Q(provisional_name=unpacked_name)
                                               )
                except Body.DoesNotExist:
                    logger.debug("Body %s does not exist" % param['body'])
                    # if no body is found, remove obsline
                    obs_lines.remove(obs_line)
                except Body.MultipleObjectsReturned:
                    logger.warning("Multiple versions of Body %s exist" % param['body'])
                # when a body is found, exit loop
                if obs_body is not None:
                    break

        if obs_body:
            # initialize DB products
            frame_list = Frame.objects.filter(sourcemeasurement__body=obs_body)
            for obs_line in reversed(obs_lines):
                frame = None
                logger.debug(obs_line.rstrip())
                params = parse_mpcobs(obs_line)
                if params:
                    # Check name is still the same as obs_body
                    try:
                        unpacked_name = packed_to_normal(params['body'])
                    except PackedError:
                        try:
                            unpacked_name = str(int(params['body']))
                        except ValueError:
                            unpacked_name = 'ZZZZZZ'
                    # if new name, reset obs_body
                    if params['body'] != obs_body.name and unpacked_name != obs_body.provisional_name and unpacked_name != obs_body.name and params['body'] != obs_body.provisional_name:
                        try:
                            try:
                                unpacked_name = packed_to_normal(params['body'])
                            except PackedError:
                                try:
                                    unpacked_name = str(int(params['body']))
                                except ValueError:
                                    unpacked_name = 'ZZZZZZ'
                            obs_body = Body.objects.get(Q(provisional_name__startswith=params['body']) |
                                                        Q(name=params['body']) |
                                                        Q(name=unpacked_name)
                                                       )
                        except Body.DoesNotExist:
                            logger.debug("Body %s does not exist" % params['body'])
                            continue
                        except Body.MultipleObjectsReturned:
                            logger.warning("Multiple versions of Body %s exist" % params['body'])
                            continue

                    if frame_list and params['obs_type'] != 's':
                        frame = next((frm for frm in frame_list if frm.sitecode == params['site_code'] and params['obs_date'] == frm.midpoint), None)
                    if frame:
                        measure_params = {  'body'    : obs_body,
                                            'frame'   : frame,
                                            'obs_ra'  : params['obs_ra'],
                                            'obs_dec' : params['obs_dec'],
                                            'obs_mag' : params['obs_mag'],
                                            'flags'   : params['flags']
                                         }
                        try:
                            measure = SourceMeasurement.objects.get(**measure_params)
                            measure.astrometric_catalog = params['astrometric_catalog']
                            measure.save()
                            measures.append(measure)
                        except SourceMeasurement.DoesNotExist:
                            continue

            logger.info("Examined %d MPC Observations for Body #%d (%s)" % (len(measures), obs_body.pk, obs_body.current_name()))

        # Reverse and return measures.
        measures = [m for m in reversed(measures)]
        return measures

