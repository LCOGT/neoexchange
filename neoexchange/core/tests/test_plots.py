from unittest import skipIf
from datetime import datetime

from django.test import TestCase

# Import module methods to test
from core.plots import find_existing_vis_file, determine_plot_valid

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
