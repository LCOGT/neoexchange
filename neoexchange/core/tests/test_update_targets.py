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
class TestUpdateTargets(TestCase):

    def setUp(self):
        """These are the times that the bodies ingest_time, update_age, and date can be set to."""
        one_day = datetime.now() - timedelta(days=1)  
        two_days = datetime.now() - timedelta(days=2)
        three_days = datetime.now() - timedelta(days=3)  
        five_days = datetime.now() - timedelta(days=5)  
        seven_days = datetime.now() - timedelta(days=7)  
        fourteen_days = datetime.now() - timedelta(days=14)  
        twentyone_days = datetime.now() - timedelta(days=21)
        one_month = datetime.now() - timedelta(days=30)      
        three_months = datetime.now() - timedelta(days=95)
        six_months = datetime.now() - timedelta(days=185)
        year = datetime.now() - timedelta(days=365)    
    
        """These are the fake Bodies that will be tested above"""
        
        object1 = Body.objects.create(
            name='NASA1',
            origin='N',
            active=True,
            updated=True,
            ingest=six_months,
            update_time=one_day
            )
            
        object2 = Body.objects.create(
            name='NASA2',
            origin='N',
            active=True,
            updated=False,
            ingest=seven_days,
            update_time=two_days
            )
        
        object3 = Body.objects.create(
            name='NASA3',
            origin='N',
            active=True,
            updated=True,
            ingest=three_months,
            update_time=three_days
            )
        
        object4 = Body.objects.create(
            name='ARECIBO1',
            origin='A',
            active=True,
            updated=False,
            ingest=year,
            update_time=twentyone_days
            )
        
        object5 = Body.objects.create(
            name='ARECIBO2',
            origin='A',
            active=True,
            updated=False,
            ingest=year,
            update_time=fourteen_days
            )
        
        object6 = Body.objects.create(
            name='ARECIBO3',
            origin='A',
            active=True,
            updated=True,
            ingest=six_months,
            update_time=three_days
            )
        
        object7 = Body.objects.create(
            name='GOLDSTONE1',
            origin='G',
            active=True,
            updated=False,
            ingest=year,
            update_time=seven_days
            )
        
        object8 = Body.objects.create(
            name='GOLDSTONE2',
            origin='G',
            active=True,
            updated=True,
            ingest=two_days,
            update_time=three_days
            )
        
        object9 = Body.objects.create(
            name='GOLDSTONE3',
            origin='G',
            active=True,
            updated=True,
            ingest=six_months,
            update_time=five_days
            )
       
        object10 = Body.objects.create(
            name='MPC1',
            origin='M',
            active=True,
            updated=False,
            ingest=twentyone_days,
            update_time=five_days
            )
        
        object11 = Body.objects.create(
            name='MPC2',
            origin='M',
            active=True,
            updated=True,
            ingest=three_months,
            update_time=one_month
            )
        
        object12 = Body.objects.create(
            name='MPC3',
            origin='M',
            active=True,
            updated=True,
            ingest=six_months,
            update_time=one_day
            )
        
        object13 = Body.objects.create(
            name='SPACEWATCH',
            origin='S',
            active=True,
            updated=False,
            ingest=three_months,
            update_time=twentyone_days
            )
            
        object14 = Body.objects.create(
            name='A&G1',
            origin='R',
            active=True,
            updated=True,
            ingest=year,
            update_time=three_days
            )
        
        object15 = Body.objects.create(
            name='A&G2',
            origin='R',
            active=True,
            updated=False,
            ingest=three_months,
            update_time=fourteen_days
            )
        
        object16 = Body.objects.create(
            name='A&G3',
            origin='R',
            active=True,
            updated=True,
            ingest=six_months,
            update_time=two_days
            )
            
        object17 = Body.objects.create(
            name='NEODSYS',
            origin='D',
            active=True,
            updated=False,
            ingest=year,
            update_time=seven_days
            )
        
        object18 = Body.objects.create(
            name='LCO1',
            origin='L',
            active=True,
            updated=False,
            ingest=six_months,
            update_time=seven_days
            )
            
        object19 = Body.objects.create(
            name='LCO2',
            origin='L',
            active=True,
            updated=True,
            ingest=three_months,
            update_time=two_days
            )
            
        object20 = Body.objects.create(
            name='LCO3',
            origin='L',
            active=True,
            updated=True,
            ingest=three_days,
            update_time=one_day
            )

    def test_command_all_oldies(self, mock_update_MPC_orbit, mock_random_delay):
        update = update_neos(origins=['M', 'N', 'S', 'D', 'G', 'A', 'R', 'L', 'Y'], ingest_limit=90)
        updated = ['NASA1', 'MPC3', 'A&G3', 'LCO2']

        for i in updated:
            self.assertIn(i, update)

    def test_command_all_thirtysix(self, mock_update_MPC_orbit, mock_random_delay):
        update = update_neos(origins=['M', 'N', 'S', 'D', 'G', 'A', 'R', 'L', 'Y'], updated_time=30, ingest_limit=180)
        updated = ['NASA1', 'ARECIBO1', 'ARECIBO2', 'ARECIBO3', 'GOLDSTONE1', 'GOLDSTONE3', 'MPC3', 'A&G1', 'A&G3', 'NEODSYS', 'LCO1']

        for i in updated:
            self.assertIn(i, update)
        
    def test_command_nasa_oldies_nine(self, mock_update_MPC_orbit, mock_random_delay):
        update = update_neos(origins=['N', 'G'], updated_time=29, ingest_limit=180)
        updated = ['NASA1', 'GOLDSTONE1', 'GOLDSTONE3']

        for i in updated:
            self.assertIn(i, update)

    def test_command_nasa_twentyfour(self, mock_update_MPC_orbit, mock_random_delay):
        update = update_neos(origins=['N', 'G'], updated_time=8)
        updated = ['NASA1', 'GOLDSTONE3']

        for i in updated:
            self.assertIn(i, update)

    def test_command_incorrect_time(self, mock_update_MPC_orbit, mock_random_delay):
        with self.assertRaisesRegexp(ValueError, 'Check the format of your date; it should look like this:%y-%m-%d %H:%M:%S'):
            update_neos(start_time='2015/07/21 21:00:00')

    def test_command_objects_six(self, mock_update_MPC_orbit, mock_random_delay):
        update = update_neos(origins=['N', 'S', 'D', 'G', 'A', 'R'], updated_time=6)
        updated = ['NASA1', 'NASA3', 'ARECIBO3', 'GOLDSTONE3', 'A&G1', 'A&G3']

        for i in updated:
            self.assertIn(i, update)

    def test_command_radar_eighteen_oldies(self, mock_update_MPC_orbit, mock_random_delay):
        update = update_neos(origins=['A', 'G', 'R'], updated_time=22, ingest_limit=180)
        updated = ['ARECIBO1', 'ARECIBO2', 'ARECIBO3', 'GOLDSTONE1', 'GOLDSTONE3', 'A&G1', 'A&G3']

        for i in updated:
            self.assertIn(i, update)

    def test_command_radar_fifteen_datetime(self, mock_update_MPC_orbit, mock_random_delay):
        update = update_neos(origins=['A', 'G', 'R'], updated_time=45, start_time=datetime.now()-timedelta(days=30))
        updated = ['ARECIBO2', 'ARECIBO3', 'GOLDSTONE3', 'A&G1']

        for i in updated:
            self.assertIn(i, update)

    def test_all_string_time(self, mock_update_MPC_orbit, mock_random_delay):
        update = update_neos(origins=['M', 'N', 'S', 'D', 'G', 'A', 'R', 'L', 'Y'], start_time='2016-01-23 15:00:00')
        updated = []

        for i in updated:
            self.assertIn(i, update)

    def test_none_updated(self, mock_update_MPC_orbit, mock_random_delay):
        update = update_neos(origins=['M', 'N', 'S', 'D', 'G', 'A', 'R', 'L', 'Y'], updated_time=0, ingest_limit=90)
        updated = []

        for i in updated:
            self.assertIn(i, update)

