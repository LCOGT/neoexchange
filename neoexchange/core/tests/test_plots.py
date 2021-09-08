import os
from unittest import skipIf
from datetime import datetime, timedelta

from django.test import TestCase
from django.http import HttpResponse
from django.core.files.storage import default_storage

from core.models import Body
# Import module methods to test
from core.plots import find_existing_vis_file, determine_plot_valid, make_visibility_plot

# Disable logging during testing
import logging
logger = logging.getLogger(__name__)
# Disable anything below CRITICAL level
logging.disable(logging.CRITICAL)

@skipIf(True, "Needs Mocks")
class TestFindExistingVisFile(TestCase):
    # XXX Need to work out how to mock default_storage in both local and S3 mode
    def test_all_the_things(self):
        pass

class TestDeterminePlotValid(TestCase):

    def test_old_hoursup(self):

        orig_vis_file = 'visibility/42/2013XA22_hoursup_20191001-20191101.png'
        compare_time = datetime(2019,10,21,1,2,3)

        vis_file = determine_plot_valid(orig_vis_file, compare_time)

        self.assertEqual('', vis_file)

    def test_new_hoursup(self):

        orig_vis_file = 'visibility/42/2013XA22_hoursup_20191001-20191101.png'
        compare_time = datetime(2019,10,14,23,59,59)

        vis_file = determine_plot_valid(orig_vis_file, compare_time)

        self.assertEqual(orig_vis_file, vis_file)

    def test_old_hoursup_2names(self):

        orig_vis_file = 'visibility/42/12345_2013XA22_hoursup_20191001-20191101.png'
        compare_time = datetime(2019,10,21,1,2,3)

        vis_file = determine_plot_valid(orig_vis_file, compare_time)

        self.assertEqual('', vis_file)

    def test_new_hoursup_2names(self):

        orig_vis_file = 'visibility/42/12345_2013XA22_hoursup_20191001-20191101.png'
        compare_time = datetime(2019,10,14,23,59,59)

        vis_file = determine_plot_valid(orig_vis_file, compare_time)

        self.assertEqual(orig_vis_file, vis_file)

    def test_old_uncertainty(self):

        orig_vis_file = 'visibility/42/2013XA22_uncertainty_20191001-20191101.png'
        compare_time = datetime(2019,10,2,1,2,3)

        vis_file = determine_plot_valid(orig_vis_file, compare_time)

        self.assertEqual('', vis_file)

    def test_new_uncertainty(self):

        orig_vis_file = 'visibility/42/2013XA22_uncertainty_20191001-20191101.png'
        compare_time = datetime(2019,10,1,23,59,59)

        vis_file = determine_plot_valid(orig_vis_file, compare_time)

        self.assertEqual(orig_vis_file, vis_file)


class TestMakeVisibilityPlot(TestCase):

    def setUp(self):
        body_params = {
                         'provisional_name': None,
                         'provisional_packed': 'j5432',
                         'name': '455432',
                         'origin': 'A',
                         'source_type': 'N',
                         'elements_type': 'MPC_MINOR_PLANET',
                         'active': True,
                         'fast_moving': True,
                         'urgency': None,
                         'epochofel': datetime(2019, 7, 31, 0, 0),
                         'orbit_rms': 0.46,
                         'orbinc': 31.23094,
                         'longascnode': 301.42266,
                         'argofperih': 22.30793,
                         'eccentricity': 0.3660154,
                         'meandist': 1.7336673,
                         'meananom': 352.55084,
                         'perihdist': None,
                         'epochofperih': None,
                         'abs_mag': 18.54,
                         'slope': 0.15,
                         'score': None,
                         'discovery_date': datetime(2003, 9, 7, 3, 7, 18),
                         'num_obs': 130,
                         'arc_length': 6209.0,
                         'not_seen': 3.7969329574421296,
                         'updated': True,
                         'ingest': datetime(2019, 7, 4, 5, 28, 39),
                         'update_time': datetime(2019, 7, 30, 19, 7, 35)
                        }
        self.test_body = Body.objects.create(**body_params)
        self.targetname = '455432_2003RP8'

        body_params['provisional_name'] = 'N999foo'
        body_params['provisional_packed'] = None
        body_params['name'] = None
        self.test_neocp_body = Body.objects.create(**body_params)

        self.start_time = datetime(2021,6,1)
        self.end_time = self.start_time + timedelta(days=31)

    def test_badplottype(self):
        response = make_visibility_plot(None, self.test_body.pk, 'cucumber', self.start_time)

        self.assertTrue(isinstance(response, HttpResponse))
        self.assertEqual('image/gif', response['Content-Type'])
        self.assertEqual(b'GIF89a', response.content[0:6])

    def test_nonameobject(self):
        response = make_visibility_plot(None, self.test_neocp_body.pk, 'radec', self.start_time)

        self.assertTrue(isinstance(response, HttpResponse))
        self.assertEqual(b'', response.content)

    def test_plot_radec(self):

        plot_filename = "visibility/{}/{}_radec_{}-{}.png".format(self.test_body.pk,
            self.targetname, self.start_time.strftime("%Y%m%d"), self.end_time.strftime("%Y%m%d"))

        response = make_visibility_plot(None, self.test_body.pk, 'radec', self.start_time)

        self.assertTrue(isinstance(response, HttpResponse))
        self.assertEqual('image/png', response['Content-Type'])
        self.assertEqual(b'\x89PNG\r\n', response.content[0:6])
        self.assertTrue(default_storage.exists(plot_filename))

    def test_plot_gallonglat(self):

        plot_filename = "visibility/{}/{}_glonglat_{}-{}.png".format(self.test_body.pk,
            self.targetname, self.start_time.strftime("%Y%m%d"), self.end_time.strftime("%Y%m%d"))

        response = make_visibility_plot(None, self.test_body.pk, 'glonglat', self.start_time)

        self.assertTrue(isinstance(response, HttpResponse))
        self.assertEqual('image/png', response['Content-Type'])
        self.assertEqual(b'\x89PNG\r\n', response.content[0:6])
        self.assertTrue(default_storage.exists(plot_filename))
