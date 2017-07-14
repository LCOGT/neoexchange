from django.core.management import call_command
from django.test import TestCase
from django.utils.six import StringIO

from datetime import datetime, timedelta

import unittest
from unittest.mock import patch, MagicMock

from core.models import Body
from core.management.commmands.update_targets import *

@patch('core.view.update_MPC_orbit')


class TestUpdate_Targets(TestCase):
            
    def test_command_nasa_oldies_nine(self, mock_update_MPC_orbit):
        
        out = StringIO()
        call_command('--sources=nasa', '--old=True', '--time=32400')
        objects = [
            messages.never.format(time=messages.timenow, name='NASA2', source='N'), 
            messages.notInThreeMonths(time=messages.timenow, name='NASA3', source='N', date=setup_time.fourtyeight_hours), 
            messages.never.format(time=messages.timenow, name='GOLDSTONE1', source='G'), 
            message.never.format(time=messages.timenow, name='GOLDSTONE2', source='G')
            ]
        expected_output = messeges.prep + messages.lenght.format(time=messages.timenow, number=6) + objects + messages.updatedNEOs.format(time=messages.timenow,updated_number=4)
        self.assertMultiLineEqual(expected_output, out)

    def test_command_radar_fifteen(self, mock_update_MPC_orbit):
        out = StringIO()
        call_command('--sources=radar', '--time=54000')
        objects =[

        expected_output = messeges.prep + messages.lenght.format(time=messages.timenow, number=9) + objects + messages.updatedNEOs.format(time=messages.timenow,updated_number=6)
        self.assertMultiLineEqual(expected_output, out)
        #self.assertIn('==== Updated 6 NEOs ====', out.getvalue())

    def test_command_all_oldies(self, mock_update_MPC_orbit):
        out = StringIO()
        call_command('--sources=allneos', '--old=True')
        objects = [

        expected_output = messeges.prep + messages.lenght.format(time=messages.timenow, number=20) + objects + messages.updatedNEOs.format(time=messages.timenow,updated_number=16)
        self.assertMultiLineEqual(expected_output, out)
        #self.assertIn('==== Updated 16 NEOs ====', out.getvalue())
        
    def test_command_objects(self, mock_update_MPC_orbit):
        out = StringIO()
        call_command('--sources=objects')
        objects = [

        expected_output = messeges.prep + messages.lenght.format(time=messages.timenow, number=14) + objects + messages.updatedNEOs.format(time=messages.timenow,updated_number=14)
        self.assertMultiLineEqual(expected_output, out)
        #self.assertIn('==== Updated 14 NEOs ====', out.getvalue())

    def test_command_radar_eighteen_oldies(self, mock_update_MPC_orbit):
        out = StringIO()
        call_command('--sources=radar', '--time=64800', '--old=True')
        objects =[

        expected_output = messeges.prep + messages.lenght.format(time=messages.timenow, number=9) + objects + messages.updatedNEOs.format(time=messages.timenow,updated_number=7)
        self.assertMultiLineEqual(expected_output, out)
        #self.assertIn('==== Updated 7 NEOs ====', out.getvalue())

    def test_command_nasa_twentyfour(self, mock_update_MPC_orbit):
        out = StringIO()
        call_command('--sources=nasa', '--time=86400')
        objects = [
            ]
        expected_output = messeges.prep + messages.lenght.format(time=messages.timenow, number=6) + objects + messages.updatedNEOs.format(time=messages.timenow,updated_number=4)
        self.assertMultiLineEqual(expected_output, out)
        #self.assertIn('==== Updated 4 NEOs ====', out.getvalue())
        
    def test_command_all_thirtysix(self, mock_update_MPC_orbit):
        out = StringIO()
        call_command('--sources=allneos', '--time=129600')
        objects = [

        expected_output = messeges.prep + messages.lenght.format(time=messages.timenow, number=20) + objects + messages.updatedNEOs.format(time=messages.timenow,updated_number=12)
        self.assertMultiLineEqual(expected_output, out)
        #self.assertIn('==== Updated 12 NEOs ====', out.getvalue())

    def test_command_objects_six(self, mock_update_MPC_orbit):
        out = StringIO()
        call_command('--sources=objects', '--time=21600')
        objects = [
        expected_output = messeges.prep + messages.lenght.format(time=messages.timenow, number=14) + objects + messages.updatedNEOs.format(time=messages.timenow,updated_number=10)
        self.assertMultiLineEqual(expected_output, out)
        #self.assertIn('==== Updated 10 NEOs ====', out.getvalue())
    ''''   
    def setup_bodies(self):

        object1=Body.objects.create(
            'name' = 'NASA1',
            'origin' = 'N',
            'active' = True,
            'updated' = True,
            'ingest' = setup_time.twentyfour_hours
            'update_time' = setup_time.six_hours
            )
            
        object2=Body.objects.create(    
            'name' = 'NASA2',
            'origin' = 'N',
            'active' = True,
            'updated' = False,
            'ingest' = setup_time.fourtyeight_hours
            'update_time' = setup_time.fourtyeight_hours
            )
        
        object3=Body.objects.create(    
            'name' = 'NASA3',
            'origin' = 'N',
            'active' = True,
            'updated' = True,
            'ingest' = setup_time.three_months
            'update_time' = setup_time.thirysix_hours
            )
        
        object4=Body.objects.create(    
            'name' = 'ARECIBO1',
            'origin' = 'A',
            'active' = True,
            'updated' = False,
            'ingest' = setup_time.eighteen_hours
            'update_time' = setup_time.eighteen_hours
            )
        
        object5=Body.objects.create(    
            'name' = 'ARECIBO2',
            'origin' = 'A',
            'active' = True,
            'updated' = False,
            'ingest' = setup_time.six_hours
            'update_time' = setup_time.six_hours
            )
        
        object6=Body.objects.create(    
            'name' = 'ARECIBO3',
            'origin' = 'A',
            'active' = True,
            'updated' = True,
            'ingest' = setup_time.six_months
            'update_time' = setup_time.three_months
            )
        
        object7=Body.objects.create(    
            'name' = 'GOLDSTONE1',
            'origin' = 'G',
            'active' = True,
            'updated' = False,
            'ingest' = setup_time.year
            'update_time' = setup_time.year
            )
        
        object8=Body.objects.create(    
            'name' = 'GOLDSTONE2'
            'origin' = 'G'
            'active' = True
            'updated' = True
            'ingest' = setup_time.fourtyeight_hours
            'update_time' = setup_time.three_hours
            )
        
        object9=Body.objects.create(
            'name' = 'GOLDSTONE3'
            'origin' = 'G'
            'active' = True
            'updated' = False
            'ingest' = setup_time.six_months
            'update_time' = setup_time.six_months
            )
        
        object10=Body.objects.create(    
            'name' = 'MPC1'
            'origin' = 'M'
            'active' = True
            'updated' = False
            'ingest' = setup_time.twelve_hours
            'update_time' = setup_time.twelve_hours
            )
        
        object11=Body.objects.create(    
            'name' = 'MPC2'
            'origin' = 'M'
            'active' = True
            'updated' = True
            'ingest' = setup_time.twentyfour_hours
            'update_time' = setup_time.six_hours
            )
        
        object12=Body.objects.create(
            'name' = 'MPC3'
            'origin' = 'M'
            'active' = True
            'updated' = True
            'ingest' = setup_time.three_months
            'update_time' = setup_time.twelve_hours
            )
        
        object13=Body.objects.create(    
            'name' = 'SPACEWATCH'
            'origin' = 'S'
            'active' = True
            'updated' = False
            'ingest' = setup_time.twentyfour_hours
            'update_time' = setup_time.twentyfour_hours
            )
            
        object14=Body.objects.create(    
            'name' = 'A&G1'
            'origin' = 'R'
            'active' = True
            'updated' = True
            'ingest' = setup_time.six_hours
            'update_time' = setup_time.three_hours
            )
        
        object15=Body.objects.create(    
            'name' = 'A&G2'
            'origin' = 'R'
            'active' = True
            'updated' = False
            'ingest' = setup_time.twelve_hours
            'update_time' = setup_time.twelve_hours
            )
        
        object16=Body.objects.create(    
            'name' = 'A&G3'
            'origin' = 'R'
            'active' = True
            'updated' = False
            'ingest' = setup_time.thirtysix_hours
            'update_time' = setup_time.thirtysix_hours
            )

        object17=Body.objects.create(
            'name' = 'NEODSYS'
            'origin' = 'D'
            'active' = True
            'updated' = False
            'ingest' = setup_time.year
            'update_time' = setup_time.eighteen_hours
            )
        

        object18=Body.objects.create(        
            'name' = 'LCO1'
            'origin' = 'L'
            'active' = True
            'updated' = False
            'ingest' = setup_time.six_hours
            'update_time' = setup_time.six_hours
            )

        object19=Body.objects.create(
            'name' = 'LCO2'
            'origin' = 'L'
            'active' = True
            'updated' = True
            'ingest' = setup_time.three_months
            'update_time' = setup_time.fourtyeight_hours
            )

        object20=Body.objects.create(        
            'name' = 'LCO3'
            'origin' = 'L'
            'active' = True
            'updated' = True
            'ingest' = setup_time.twentyfour_hours
            'update_time' = setup_time.eighteen_hours
            )
'''
    def setup_time(self):
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
        prep = '[{time}] INFO ==== Preparing to Updating Targets {time} ===='.format(time=timenow)
        lenght = '[{time}] INFO Length of target query set to check {number}'
        never = '[{time}] INFO Updating {name} from {source} which was Never Updated'
        previously = '[{time}] INFO Updating {name} from {source} which was Previously Updated on {date}'
        notInThreeMonths = '[{time}] INFO Updating {name} from {source} which was Not Updated in Three Months on {date}'
        updateNEOs = '[{time}] INFO ==== Updated {updated_number} NEOs ===='
        noNEOs ='[{time}] INFO ==== No NEOs to be updated ===='.format(time=timenow)

    
    
    

