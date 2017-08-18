from django.core.management import call_command
from django.test import TestCase
from django.utils.six import StringIO

from datetime import datetime, timedelta
import logging
import unittest
from mock import patch, Mock

from core.models import Body
from core.views import *

@patch('astrometrics.sources_subs.random_delay')
@patch('core.views.update_MPC_orbit')

class TestUpdate_Targets(TestCase):

    def setUp(self):
        """These are the times that the bodies ingest and update_time can be set to."""
        #these are just under the number of hours their name says they are
        three_hours = datetime.now() - timedelta(hours=2, minutes=55)
        six_hours = datetime.now()- timedelta(hours=5, minutes=55)
        twelve_hours = datetime.now() - timedelta(hours=11, minutes=55)
        eighteen_hours = datetime.now() - timedelta(hours=17, minutes=55)
        twentyfour_hours = datetime.now() - timedelta(hours=23, minutes=55)
        thirtysix_hours = datetime.now() - timedelta(hours=35, minutes=55)
        fourtyeight_hours = datetime.now() - timedelta(hours=47,minutes=55)
        three_months = datetime.now() - timedelta(days=85)
        six_months = datetime.now() - timedelta(days=175)
        year = datetime.now() - timedelta(days=355)    
    
        """These are the fake Bodies that will be tested above"""
        
        object1=Body.objects.create(
            name='NASA1',
            origin='N',
            active=True,
            updated=True,
            ingest=six_months,
            update_time=six_hours
            )
            
        object2=Body.objects.create(
            name='NASA2',
            origin='N',
            active=True,
            updated=False,
            ingest=fourtyeight_hours,
            update_time=fourtyeight_hours
            )
        
        object3=Body.objects.create(
            name='NASA3',
            origin='N',
            active=True,
            updated=True,
            ingest=three_months,
            update_time=thirtysix_hours
            )
        
        object4=Body.objects.create(
            name='ARECIBO1',
            origin='A',
            active=True,
            updated=False,
            ingest=year,
            update_time=eighteen_hours
            )
        
        object5=Body.objects.create(
            name='ARECIBO2',
            origin='A',
            active=True,
            updated=False,
            ingest=six_hours,
            update_time=six_hours
            )
        
        object6=Body.objects.create(
            name='ARECIBO3',
            origin='A',
            active=True,
            updated=True,
            ingest=six_months,
            update_time=three_months
            )
        
        object7=Body.objects.create(
            name='GOLDSTONE1',
            origin='G',
            active=True,
            updated=False,
            ingest=year,
            update_time=year
            )
        
        object8=Body.objects.create(
            name='GOLDSTONE2',
            origin='G',
            active=True,
            updated=True,
            ingest=fourtyeight_hours,
            update_time=three_hours
            )
        
        object9=Body.objects.create(
            name='GOLDSTONE3',
            origin='G',
            active=True,
            updated=True,
            ingest=six_months,
            update_time=six_months
            )
       
        object10=Body.objects.create(
            name='MPC1',
            origin='M',
            active=True,
            updated=False,
            ingest=twelve_hours,
            update_time=twelve_hours
            )
        
        object11=Body.objects.create(
            name='MPC2',
            origin='M',
            active=True,
            updated=True,
            ingest=three_months,
            update_time=six_hours
            )
        
        object12=Body.objects.create(
            name='MPC3',
            origin='M',
            active=True,
            updated=True,
            ingest=three_months,
            update_time=twelve_hours
            )
        
        object13=Body.objects.create(
            name='SPACEWATCH',
            origin='S',
            active=True,
            updated=False,
            ingest=twentyfour_hours,
            update_time=twentyfour_hours
            )
            
        object14=Body.objects.create(
            name='A&G1',
            origin='R',
            active=True,
            updated=True,
            ingest=six_hours,
            update_time=three_hours
            )
        
        object15=Body.objects.create(
            name='A&G2',
            origin='R',
            active=True,
            updated=False,
            ingest=twelve_hours,
            update_time=twelve_hours
            )
        
        object16=Body.objects.create(
            name='A&G3',
            origin='R',
            active=True,
            updated=True,
            ingest=six_months,
            update_time=thirtysix_hours
            )
            
        object17=Body.objects.create(
            name='NEODSYS',
            origin='D',
            active=True,
            updated=False,
            ingest=year,
            update_time=eighteen_hours
            )
        
        object18=Body.objects.create(      
            name='LCO1',
            origin='L',
            active=True,
            updated=False,
            ingest=six_hours,
            update_time=six_hours
            )
            
        object19=Body.objects.create(
            name='LCO2',
            origin='L',
            active=True,
            updated=True,
            ingest=three_months,
            update_time=fourtyeight_hours
            )
            
        object20=Body.objects.create(
            name='LCO3',
            origin='L',
            active=True,
            updated=True,
            ingest=twentyfour_hours,
            update_time=eighteen_hours
            )
            
#update_neos(origins=origins, updated_time=time, ingest_limit=old, never_update=never, start_time=date)         
    def test_command_all_oldies(self, mock_update_MPC_orbit, mock_random_delay):
        update = update_neos(origins=['M', 'N', 'S', 'D', 'G', 'A', 'R', 'L'], ingest_limit=90)
        updated = ['NASA2', 'NASA3', 'ARECIBO2', 'GOLDSTONE2', 'MPC1', 'MPC2', 'MPC3', 'SPACEWATCH', 'A&G1', 'A&G2', 'LCO1', 'LCO2', 'LCO3']
	
        for i in updated:
	        self.assertIn(i, update)

    def test_command_all_thirtysix(self, mock_update_MPC_orbit, mock_random_delay):
        update = update_neos(origins=['M', 'N', 'S', 'D', 'G', 'A', 'R', 'L'], updated_time=36, ingest_limit=10)
        updated = ['ARECIBO2', 'GOLDSTONE2', 'MPC1', 'SPACEWATCH', 'A&G1', 'A&G2', 'LCO1', 'LCO3']

        for i in updated:
	        self.assertIn(i, update)
        
    def test_command_nasa_oldies_nine(self, mock_update_MPC_orbit, mock_random_delay):
        update = update_neos(origins=['N','G'], updated_time=9, ingest_limit=185)
        updated = ['NASA1', 'GOLDSTONE2']

        for i in updated:
	        self.assertIn(i, update)    

    def test_command_nasa_twentyfour(self, mock_update_MPC_orbit, mock_random_delay):
        update = update_neos(origins=['N','G'], updated_time=24)
        updated = ['GOLDSTONE2']

        for i in updated:
	        self.assertIn(i, update)

    def test_command_incorrect_time(self, mock_update_MPC_orbit, mock_random_delay):
        update = update_neos(start_time='2015/07/21 21:00:00')

        self.assertRaises(ValueError, update)

    def test_command_objects_six(self, mock_update_MPC_orbit, mock_random_delay):
        update = update_neos(origins=['N', 'S', 'D', 'G', 'A', 'R'], updated_time=6)
        updated = ['ARECIBO2', 'GOLDSTONE2', 'A&G1']
        
        for i in updated:
	        self.assertIn(i, update)

    def test_command_radar_eighteen_oldies(self, mock_update_MPC_orbit, mock_random_delay):
        update = update_neos(origins=['A','G','R'], updated_time=18, ingest_limit=185)
        updated = ['ARECIBO2', 'GOLDSTONE2', 'A&G1', 'A&G2']

        for i in updated:
	        self.assertIn(i, update)
        
    def test_command_radar_fifteen_datetime(self, mock_update_MPC_orbit, mock_random_delay):
        update = update_neos(origins=['A', 'G', 'R'], updated_time=15, start_time=datetime.now()-timedelta(days=30))
        updated = ['ARECIBO2', 'GOLDSTONE2', 'A&G1', 'A&G2']
        
        for i in updated:
	        self.assertIn(i, update)
        
    def test_all_string_time(self, mock_update_MPC_orbit, mock_random_delay):
        update = update_neos(origins=['M', 'N', 'S', 'D', 'G', 'A', 'R', 'L', 'Y'], start_time='2017-01-23 15:00:00')
        updated = ['NASA2', 'NASA3', 'ARECIBO2', 'GOLDSTONE2', 'MPC1', 'MPC2', 'MPC3', 'SPACEWATCH', 'A&G1', 'A&G2', 'LCO1', 'LCO2', 'LCO3']

        for i in updated:
	        self.assertIn(i, update)
        
    def test_none_updated(self, mock_update_MPC_orbit, mock_random_delay):
        update = update_neos(origins=['M', 'N', 'S', 'D', 'G', 'A', 'R', 'L', 'Y'], updated_time=0, ingest_limit=90)
        updated = []
        
        for i in updated:
	        self.assertIn(i, update)

