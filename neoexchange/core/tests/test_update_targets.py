from django.core.management import call_command
from django.test import TestCase
from django.utils.six import StringIO

from datetime import datetime, timedelta
import logging
import unittest
from mock import patch, MagicMock

from core.models import Body
from core.management.commands.update_targets import *

@patch('core.views.update_MPC_orbit')
@patch('astrometrics.sources_subs.random_delay')


class TestUpdate_Targets(TestCase):
  
    def test_command_nasa_oldies_nine(self, mock_update_MPC_orbit, mock_random_delay):
        now = datetime.now()
        expected_updated = ['NASA2','NASA3','GOLDSTONE1','GOLDSTONE3']
        expected_updated_sources = ['N','N','G','G']
        expected_updated_bool = [True, True, True, True]
        expected_updated_time = [now, now, now, now]
        updated = update_targets.update_neos(origins=['N','G'], time=43200, old=True)
        
        self.assertListEqual(expected_updated, updated[0])
        self.assertListEqual(expected_updated_sources, updated[1])
        self.assertListEqual(expected_updated_bool, updated[2])
        self.assertListEqual(expected_updated_time, updated[3])

    def test_command_radar_fifteen(self, mock_update_MPC_orbit, mock_random_delay):
        now = datetime.now()
        expected_updated = ['ARECIBO1','ARECIBO2','GOLDSTONE1','A&G2','A&G3']
        expected_updated_sources = ['A','A','G','R','R']
        expected_updated_bool = [True, True, True, True, True]
        expected_updated_time = [now, now, now, now, now]
        updated = update_targets.update_neos(origins=['A', 'G', 'R'], time=54000)
        
        self.assertListEqual(expected_updated, updated[0])
        self.assertListEqual(expected_updated_sources, updated[1])
        self.assertListEqual(expected_updated_bool, updated[2])
        self.assertListEqual(expected_updated_time, updated[3])
        
    def test_command_all_oldies(self, mock_update_MPC_orbit, mock_random_delay):
        now = datetime.now()
        expected_updated = ['NASA2','ARECIBO2','ARECIBO3','GOLDSTONE1','GOLDSTONE3','MPC1','SPACEWATCH','A&G2','LCO1','LCO2']
        expected_updated_sources = ['N', 'A', 'A', 'G', 'G', 'M', 'S', 'R', 'R', 'L', 'L']
        expected_updated_bool = [True, True, True, True, True, True, True, True, True, True]
        expected_updated_time = [now, now, now, now, now, now, now, now, now, now]
        updated = update_targets.update_neos(origins=['M', 'N', 'S', 'D', 'G', 'A', 'R', 'L'], old=True)
        
        self.assertListEqual(expected_updated, updated[0])
        self.assertListEqual(expected_updated_sources, updated[1])
        self.assertListEqual(expected_updated_bool, updated[2])
        self.assertListEqual(expected_updated_time, updated[3])
        
    def test_command_objects(self, mock_update_MPC_orbit, mock_random_delay):
        now = datetime.now()
        expected_updated = ['NASA2', 'ARECIBO1', 'ARECIBO2', 'GOLDSTONE1', 'SPACEWATCH', 'A&G2', 'A&G3', 'NEODSYS']
        expected_updated_sources = ['N', 'A', 'A', 'G', 'S', 'R', 'R','D']
        expected_updated_bool = [True, True, True, True, True, True, True, True]
        expected_updated_time = [now, now, now, now, now, now, now, now]
        updated = updated_targets.update_neos()
        
        self.assertListEqual(expected_updated, updated[0])
        self.assertListEqual(expected_updated_sources, updated[1])
        self.assertListEqual(expected_updated_bool, updated[2])
        self.assertListEqual(expected_updated_time, updated[3])
        
    def test_command_radar_eighteen_oldies(self, mock_update_MPC_orbit, mock_random_delay):
        now = datetime.now()
        expected_updated = ['ARECIBO1', 'ARECIBO2', 'GOLDSTONE1']
        expected_updated_sources = ['A', 'A', 'G']
        expected_updated_bool = [True, True, True]
        expected_updated_time = [now, now, now]
        updated =  updated_targets.update_neos(origins=['A','G','R'], time=64800, old=True)

        self.assertListEqual(expected_updated, updated[0])
        self.assertListEqual(expected_updated_sources, updated[1])
        self.assertListEqual(expected_updated_bool, updated[2])
        self.assertListEqual(expected_updated_time, updated[3])

    def test_command_nasa_twentyfour(self, mock_update_MPC_orbit, mock_random_delay):
        now = datetime.now()
        expected_updated = ['NASA2', 'NASA3', 'GOLDSTONE1']
        expected_updated_sources = ['N', 'N', 'G']
        expected_updated_bool = [True, True, True]
        expected_updated_time = [now, now, now]
        updated = updated_targets.update_neos(origins=['N','G'], time=86400)
        
        self.assertListEqual(expected_updated, updated[0])
        self.assertListEqual(expected_updated_sources, updated[1])
        self.assertListEqual(expected_updated_bool, updated[2])
        self.assertListEqual(expected_updated_time, updated[3])
        
    def test_command_all_thirtysix(self, mock_update_MPC_orbit, mock_random_delay):
        now = datetime.now()
        expected_updated = ['NASA2', 'NASA3', 'ARECIBO2', 'GOLDSTONE1', 'MPC1', 'SPACEWATCH', 'A&G2', 'A&G3', 'LCO1']
        expected_updated_sources = ['N', 'N', 'A', 'G', 'M', 'S', 'R', 'R', 'L']
        expected_updated_bool = [True, True, True, True, True, True, True, True, True]
        expected_updated_time = [now, now, now, now, now, now, now, now, now]
        updated =  update_targets.update_neos(origins=['M', 'N', 'S', 'D', 'G', 'A', 'R', 'L'], time=129600)
        
        self.assertListEqual(expected_updated, updated[0])
        self.assertListEqual(expected_updated_sources, updated[1])
        self.assertListEqual(expected_updated_bool, updated[2])
        self.assertListEqual(expected_updated_time, updated[3])

    def test_command_objects_six(self, mock_update_MPC_orbit, mock_random_delay):
        now = datetime.now()
        expected_updated = ['NASA1', 'NASA2', 'ARECIBO1', 'ARECIBO2', 'GOLDSTONE1', 'SPACEWATCH', 'A&G2', 'A&G3', 'NEODSYS']
        expected_updated_sources = ['N', 'N', 'A', 'A', 'G', 'S', 'R', 'R', 'D']
        expected_updated_bool = [True, True, True, True, True, True, True, True, True]
        expected_updated_time = [now, now, now, now, now, now, now, now, now]
        call_command('--sources=objects', '--time=21600')
        
        self.assertListEqual(expected_updated, updated[0])
        self.assertListEqual(expected_updated_sources, updated[1])
        self.assertListEqual(expected_updated_bool, updated[2])
        self.assertListEqual(expected_updated_time, updated[3])

    def setup_time(self):
        """These are the times that the bodies ingest and update_time can be set to."""
        #these are just under the number of hours their name says they are
        six_hours = datetime.now()- timedelta(hours=5, minutes=55)
        twelve_hours = datetime.now() - timedelta(hours=11, minutes=55)
        eighteen_hours = datetime.now() - timedelta(hours=17, minutes=55)
        twentyfour_hours = datetime.now() - timedelta(hours=23, minutes=55)
        thirtysix_hours = datetime.now() - timedelta(hours=35, minutes=55)
        fourtyeighthours = datetime.now() - timedelta(hours=47,minutes=55)
        #just over the time their name says they are
        three_months = datetime.now() - timedelta(months=3, days=1)
        six_months = datetime.now() - timedelta(months=6, days=1)
        year = datetime.now() - timedelta(years=1, days=1)
        
    def messages(self):
        timenow = datetime.now().strftime('%Y-%m-%d %H:%M')
        prep = '==== Preparing to Updating Targets {time} ===='.format(time=timenow)
        lenght = 'Length of target query set to check {number}'
        never = 'Updating {name} from {source} which was Never Updated'
        previously = 'Updating {name} from {source} which was Previously Updated on {date}'
        old = 'Updating {name} from {source} which was Not Updated in Three Months on {date}'
        updateNEOs = '==== Updated {updated_number} NEOs ===='
        noNEOs ='==== No NEOs to be updated ===='
        

    def setup_bodies(self):
        """These are the fake Bodies that will be tested above"""
        
        object1=Body.objects.create(
            params = {
            'name' : 'NASA1',
            'origin' : 'N',
            'active' : True,
            'updated' : True,
            'ingest' : setup_time.twentyfour_hours,
            'update_time' : setup_time.six_hours
            })
            
        object2=Body.objects.create(
            params = {
            'name' : 'NASA2',
            'origin' : 'N',
            'active' : True,
            'updated' : False,
            'ingest' : setup_time.fourtyeight_hours,
            'update_time' : setup_time.fourtyeight_hours
            })
        
        object3=Body.objects.create(
            params = {
            'name' : 'NASA3',
            'origin' : 'N',
            'active' : True,
            'updated' : True,
            'ingest' : setup_time.three_months,
            'update_time' : setup_time.thirysix_hours
            })
        
        object4=Body.objects.create(
            params = {
            'name' : 'ARECIBO1',
            'origin' : 'A',
            'active' : True,
            'updated' : False,
            'ingest' : setup_time.eighteen_hours,
            'update_time' : setup_time.eighteen_hours
            })
        
        object5=Body.objects.create(
            params = {
            'name' : 'ARECIBO2',
            'origin' : 'A',
            'active' : True,
            'updated' : False,
            'ingest' : setup_time.six_hours,
            'update_time' : setup_time.six_hours
            })
        
        object6=Body.objects.create(
            params = {
            'name' : 'ARECIBO3',
            'origin' : 'A',
            'active' : True,
            'updated' : True,
            'ingest' : setup_time.six_months,
            'update_time' : setup_time.three_months
            })
        
        object7=Body.objects.create({
            'name' : 'GOLDSTONE1',
            'origin' : 'G',
            'active' : True,
            'updated' : False,
            'ingest' : setup_time.year,
            'update_time' : setup_time.year
            })
        
        object8=Body.objects.create(
            params = {
            'name' : 'GOLDSTONE2',
            'origin' : 'G',
            'active' : True,
            'updated' : True,
            'ingest' : setup_time.fourtyeight_hours,
            'update_time' : setup_time.three_hours
            })
        
        object9=Body.objects.create(
            params = {
            'name' : 'GOLDSTONE3',
            'origin' : 'G',
            'active' : True,
            'updated' : False,
            'ingest' : setup_time.six_months,
            'update_time' : setup_time.six_months
            })
       
        object10=Body.objects.create(
            params = {
            'name' : 'MPC1',
            'origin' : 'M',
            'active' : True,
            'updated' : False,
            'ingest' : setup_time.twelve_hours,
            'update_time' : setup_time.twelve_hours
            })
        
        object11=Body.objects.create(
            params = {
            'name' : 'MPC2',
            'origin' : 'M',
            'active' : True,
            'updated' : True,
            'ingest' : setup_time.twentyfour_hours,
            'update_time' : setup_time.six_hours
            })
        
        object12=Body.objects.create(
            params = {
            'name' : 'MPC3',
            'origin' : 'M',
            'active' : True,
            'updated' : True,
            'ingest' : setup_time.three_months,
            'update_time' : setup_time.twelve_hours
            })
        
        object13=Body.objects.create(
            params = {
            'name' : 'SPACEWATCH',
            'origin' : 'S',
            'active' : True,
            'updated' : False,
            'ingest' : setup_time.twentyfour_hours,
            'update_time' : setup_time.twentyfour_hours
            })
            
        object14=Body.objects.create(
            params = {
            'name' : 'A&G1',
            'origin' : 'R',
            'active' : True,
            'updated' : True,
            'ingest' : setup_time.six_hours,
            'update_time' : setup_time.three_hours
            })
        
        object15=Body.objects.create(
            params = {
            'name' : 'A&G2',
            'origin' : 'R',
            'active' : True,
            'updated' : False,
            'ingest' : setup_time.twelve_hours,
            'update_time' : setup_time.twelve_hours
            })
        
        object16=Body.objects.create(
            params = {
            'name' : 'A&G3',
            'origin' : 'R',
            'active' : True,
            'updated' : False,
            'ingest' : setup_time.thirtysix_hours,
            'update_time' : setup_time.thirtysix_hours
            })
        object17=Body.objects.create(
            params = {
            'name' : 'NEODSYS',
            'origin' : 'D',
            'active' : True,
            'updated' : False,
            'ingest' : setup_time.year,
            'update_time' : setup_time.eighteen_hours
            })
        
        object18=Body.objects.create(
            params = {        
            'name' : 'LCO1',
            'origin' : 'L',
            'active' : True,
            'updated' : False,
            'ingest' : setup_time.six_hours,
            'update_time' : setup_time.six_hours
            })
        object19=Body.objects.create(
            params = {
            'name' : 'LCO2',
            'origin' : 'L',
            'active' : True,
            'updated' : True,
            'ingest' : setup_time.three_months,
            'update_time' : setup_time.fourtyeight_hours
            })
        object20=Body.objects.create(
            params = {
            'name' : 'LCO3',
            'origin' : 'L',
            'active' : True,
            'updated' : True,
            'ingest' : setup_time.twentyfour_hours,
            'update_time' : setup_time.eighteen_hours
            })
