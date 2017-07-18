from django.core.management import call_command
from django.test import TestCase
from django.utils.six import StringIO

from datetime import datetime, timedelta
import logging
import unittest
from mock import patch, MagicMock

from core.models import Body
from core.management.commmands.update_targets import *

@patch('core.view.update_MPC_orbit')
@patch('astrometrics.sources_subs.random_delay')


class TestUpdate_Targets(TestCase):
  
    def test_command_nasa_oldies_nine(self, mock_update_MPC_orbit, mock_random_delay):
        
        self.out = logging.handle()
        call_command('--sources=nasa', '--old=True', '--time=32400')
        with self.assertLogs('logger', level='INFO') as logs:
            logging.getLogger('logger').info(messages.prep)
            logging.getLogger('logger').info(messages.lenght.format(number=6))
            logging.getLogger('logger').info(messages.never.format(name='NASA2', source='N'))
            logging.getLogger('logger').info(messages.previously.format(name='NASA3', source='N', date=setup_time.thirtysix_hours))
            logging.getLogger('logger').info(messages.never.format(name='GOLDSTONE1', source='G'))
            logging.getLogger('logger').info(messages.old.format(name='GOLDSTONE3', source='G', date=setup_time.three_months))
            logging.getLogger('logger').info(messages.updateNEOs.format(updated_number=4))
        self.assertEqual(logs.output, out.getvalue())

    def test_command_radar_fifteen(self, mock_update_MPC_orbit, mock_random_delay):
        out = StringIO()
        call_command('--sources=radar', '--time=54000')
        with self.assertLogs('logger', level='INFO') as logs:
            logging.getLogger('logger').info(messages.prep)
            logging.getLogger('logger').info(messages.lenght.format(number=9))
            logging.getLogger('logger').info(messages.previously.format(name='ARECIBO1', source='A',date=setup_time.eighteen_hours))
            logging.getLogger('logger').info(messages.never.format(name='ARECIBO2', source='A'))
            logging.getLogger('logger').info(messages.never.format(name='GOLDSTONE1', source='G'))
            logging.getLogger('logger').info(messages.never.format(name='A&G2', source='R'))
            logging.getLogger('logger').info(messages.previously.format(name='A&G3', source='R', date=setup_time.thirtysix_hours))
            logging.getLogger('logger').info(messages.updateNEOs.format(updated_number=5))
        self.assertEqual(logs.output, out.getvalue())
        
    def test_command_all_oldies(self, mock_update_MPC_orbit, mock_random_delay):
        log = logging.getLogger('logger')
        out = StringIO()
        call_command('--sources=allneos', '--old=True')
        with self.assertLogs('logger', level='INFO') as logs:
            log.info(messages.prep)
            log.info(messages.lenght.format(number=20))
            log.info(messages.never.format(name='NASA2', source='N'))
            log.info(messages.never.format(name='ARECIBO2', source='A'))
            log.info(messages.old.format(name='ARECIBO3', source='A', date=setup_time.three_months))
            log.info(messages.never.format(name='GOLDSTONE1', source='G'))
            log.info(messages.old.format(name='GOLDSTONE3', source='G', date=setup_time.three_months))
            log.info(messages.never.format(name='MPC1', source='M'))
            log.info(messages.never.format(name='SPACEWATCH', source='S'))
            log.info(messages.never.format(name='A&G2', source='R'))
            log.info(messages.never.format(name='LCO1', source='L'))
            log.info(messages.old.format(name='LCO2', source='L', date=setup_time.three_months))
            log.info(messages.updateNEOs.format(updated_number=9))
        self.assertEqual(logs.output, out)
        
    def test_command_objects(self, mock_update_MPC_orbit, mock_random_delay):
        log = logging.getLogger('logger')
        out = StringIO()
        
        call_command('--sources=objects')
        with self.assertLogs('logger', level='INFO') as logs:
            log.info(messages.prep)
            log.info(messages.lenght.format(number=14))
            log.info(messages.never.format(name='NASA2', source='N'))
            log.info(messages.old.format(name='ARECIBO1', source='A', date=setup_time.eighteen_hours))
            log.info(messages.never.format(name='ARECIBO2', source='A'))
            log.info(messages.never.format(name='GOLDSTONE1', source='G'))
            log.info(messages.never.format(name='SPACEWATCH', source='S'))
            log.info(messages.never.format(name='A&G2', source='R'))
            log.info(messages.old.format(name='A&G3', source='R', date=setup_time.thirtysix_hours))
            log.info(messages.old.format(name='NEODSYS', source='D', date=setup_time.eighteen_hours))
            logg.info(messages.updateNEOs.format(updated_number=8))
        self.assertEqual(logs.output, out)

    def test_command_radar_eighteen_oldies(self, mock_update_MPC_orbit, mock_random_delay):
        out = StringIO()
        call_command('--sources=radar', '--time=64800', '--old=True')
        with self.assertLogs('logger', level='INFO') as logs:
            logging.getLogger().info(messages.prep)
            logging.getLogger().info(messages.lenght.format(number=9))
            logging.getLogger().info(messages.previously.format(name='ARECIBO1', source='A', date=setup_time.eighteen_hours))
            logging.getLogger().info(messages.never.format(name='ARECIBO2', source='A'))
            logging.getLogger().info(messages.never.format(name='GOLDSTONE1', source='G'))
            logging.getLogger().info(messages.updateNEOs.format(updated_number=3))
        self.assertEqual(logs.output, out)

    def test_command_nasa_twentyfour(self, mock_update_MPC_orbit, mock_random_delay):
        out = StringIO()
        call_command('--sources=nasa', '--time=86400')
        with self.assertLogs('logger', level='INFO') as logs:
            logging.getLogger().info(messages.prep)
            logging.getLogger().info(messages.lenght.format(number=6))
            logging.getLogger().info(messages.never.format(name='NASA2', source='N'))
            logging.getLogger().info(messages.previously.format(name='NASA3', source='N', date=setup_time.thirtysix_hours))
            logging.getLogger().info(messages.never.format(name='GOLDSTONE1', source='G'))
            logging.getLogger().info(messages.updateNEOs.format(updated_number=3))
        self.assertEqual(logs.output, out)
        
    def test_command_all_thirtysix(self, mock_update_MPC_orbit, mock_random_delay):
        out = StringIO()
        call_command('--sources=allneos', '--time=129600')
        with self.assertLogs('logger', level='INFO') as logs:
            logging.getLogger().info(messages.prep)
            logging.getLogger().info(messages.lenght.format(number=20))
            logging.getLogger().info(messages.never.format(name='NASA2', source='N'))
            logging.getLogger().info(messages.previously.format(name='NASA3', source='N', date=setup_time.thirtysix_hours))
            logging.getLogger().info(messages.never.format(name='ARECIBO2', source='A'))
            logging.getLogger().info(messages.never.format(name='GOLDSTONE1', source='G'))
            logging.getLogger().info(messages.never.format(name='MPC1', source='M'))
            logging.getLogger().info(messages.never.format(name='SPACEWATCH', source='S'))
            logging.getLogger().info(messages.never.format(name='A&G2', source='R'))
            logging.getLogger().info(messages.previously.format(name='A&G3', source='R', date=setup_time.thirtysix_hours))
            logging.getLogger().info(messages.never.format(name='LCO1', source='L'))
            logging.getLogger().info(messages.updateNEOs.format(updated_number=4))
        self.assertEqual(logs.output, out)

    def test_command_objects_six(self, mock_update_MPC_orbit, mock_random_delay):
        out = StringIO()
        call_command('--sources=objects', '--time=21600')
        with self.assertLogs('logger', level='INFO') as logs:
            logging.getLogger().info(messages.prep)
            logging.getLogger().info(messages.lenght.format(number=14))
            logging.getLogger().info(messages.previously.format(name='NASA1', source='N', date=setup_time.six_hours))
            logging.getLogger().info(messages.never.format(name='NASA2', source='N'))
            logging.getLogger().info(messages.old.format(name='ARECIBO1', source='A', date=setup_time.eighteen_hours))
            logging.getLogger().info(messages.never.format(name='ARECIBO2', source='A'))
            logging.getLogger().info(messages.never.format(name='GOLDSTONE1', source='G'))
            logging.getLogger().info(messages.never.format(name='SPACEWATCH', source='S'))
            logging.getLogger().info(messages.never.format(name='A&G2', source='R'))
            logging.getLogger().info(messages.old.format(name='A&G3', source='R', date=setup_time.thirtysix_hours))
            logging.getLogger().info(messages.old.format(name='NEODSYS', source='D', date=setup_time.eighteen_hours))
            logging.getLogger().info(messages.updateNEOs.format(updated_number=4))
        self.assertEqual(logs.output, out)

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
        prep = '==== Preparing to Updating Targets {time} ===='.format(time=timenow)
        lenght = 'Length of target query set to check {number}'
        never = 'Updating {name} from {source} which was Never Updated'
        previously = 'Updating {name} from {source} which was Previously Updated on {date}'
        old = 'Updating {name} from {source} which was Not Updated in Three Months on {date}'
        updateNEOs = '==== Updated {updated_number} NEOs ===='
        noNEOs ='==== No NEOs to be updated ===='

    def setup_bodies(self):
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
