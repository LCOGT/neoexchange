from .base import FunctionalTest
from mock import patch
from neox.tests.mocks import MockDateTime
from datetime import datetime
from core.models import Body, PreviousSpectra

class CharacterizationPageTest(FunctionalTest):

    def insert_extra_test_body(self):
        params = {  'name'          : 'q382918r',
                    'abs_mag'       : 21.0,
                    'slope'         : 0.15,
                    'epochofel'     : '2015-03-19 00:00:00',
                    'meananom'      : 325.2636,
                    'argofperih'    : 85.19251,
                    'longascnode'   : 147.81325,
                    'orbinc'        : 8.34739,
                    'eccentricity'  : 0.1896865,
                    'meandist'      : 1.2176312,
                    'source_type'   : 'U',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'active'        : True,
                    'origin'        : 'N',
                    'ingest'        : '2015-05-11 17:20:00',
                    'score'         : 85,
                    'discovery_date': '2015-05-10 12:00:00',
                    'update_time'   : '2015-05-18 05:00:00',
                    'num_obs'       : 35,
                    'arc_length'    : 42.0,
                    'not_seen'      : 2.22,
                    'updated'       : False
                    }
        self.body, created = Body.objects.get_or_create(pk=3, **params)

        spectra_params = {'body'         : self.body,
                          'spec_wav'     : 'NIR',
                          'spec_ir'     : 'sp233/a265962.sp233.txt',
                          'spec_ref'     : 'sp[233]',
                          'spec_source'  : 'S',
                          'spec_date'    : '2017-09-25',
                          }
        self.test_spectra = PreviousSpectra.objects.create(pk=4, **spectra_params)

        spectra_params2 = {'body'         : self.body,
                          'spec_wav'     : 'NA',
                          'spec_source'  : 'M',
                          'spec_date'    : '2017-08-25',
                          }
        self.test_spectra2 = PreviousSpectra.objects.create(pk=5, **spectra_params2)

    def insert_another_extra_test_body(self):
        params = {  'name'          : 'V38821zi',
                    'abs_mag'       : 21.0,
                    'slope'         : 0.15,
                    'epochofel'     : '2015-03-19 00:00:00',
                    'meananom'      : 325.2636,
                    'argofperih'    : 85.19251,
                    'longascnode'   : 147.81325,
                    'orbinc'        : 8.34739,
                    'eccentricity'  : 0.1896865,
                    'meandist'      : 1.2176312,
                    'source_type'   : 'U',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'active'        : True,
                    'origin'        : 'G',
                    'ingest'        : '2015-05-11 17:20:00',
                    'score'         : 100,
                    'discovery_date': '2015-05-10 12:00:00',
                    'update_time'   : '2015-05-18 05:00:00',
                    'num_obs'       : 2,
                    'arc_length'    : 0.07,
                    'not_seen'      : 12.29,
                    'updated'       : False
                    }
        self.body, created = Body.objects.get_or_create(pk=4, **params)

        spectra_params = {'body'         : self.body,
                          'spec_wav'     : 'NIR',
                          'spec_ir'      : 'sp234/a096631.sp234.txt',
                          'spec_source'  : 'S',
                          'spec_date'    : '2017-09-25',
                          }
        self.test_spectra = PreviousSpectra.objects.create(pk=6, **spectra_params)

        spectra_params3 = {'body'         : self.body,
                          'spec_wav'     : 'Vis',
                          'spec_vis'     : 'sp233/a265962.sp234.txt',
                          'spec_source'  : 'S',
                          'spec_date'    : '2010-10-25',
                          }
        self.test_spectra3 = PreviousSpectra.objects.create(pk=7, **spectra_params3)

# The characterization page computes the RA, Dec of each body for 'now' so we need to mock
# patch the datetime used by models.Body.compute_position to give the same
# consistent answer.

    @patch('core.models.datetime', MockDateTime)
    def test_characterization_page(self):

        MockDateTime.change_datetime(2015, 7, 1, 17, 0, 0)
        self.insert_extra_test_body()
        self.insert_another_extra_test_body()

        #Kildorn the Unstoppable goes to the characterization page and expects to see the list of bodies in need of Characterization.
        characterization_page_url = self.live_server_url + '/characterization/'
        self.browser.get(characterization_page_url)
        self.assertNotIn('Home | LCO NEOx', self.browser.title)
        self.assertIn('Characterization Page | LCO NEOx', self.browser.title)
        self.check_for_header_in_table('characterization_targets',\
            'Rank Target Name R.A. Dec. V Mag. Required Observations H Mag. Origin SMASS Obs MANOS Target? Observation Window Reported?')

        # Position below computed for 2015-07-01 17:00:00
        testlines =[u'2 V38821zi 23 43 12.75 +19 58 55.6 20.7 LC 21.0 Goldstone Vis+NIR NO',
                    u'1 q382918r 23 43 12.75 +19 58 55.6 20.7 Spec/LC 21.0 NASA NIR YES']
        self.check_for_row_in_table('characterization_targets', testlines[0])
        self.check_for_row_in_table('characterization_targets', testlines[1])

        #He notices that they are ordered somehow
        
        #Kildorn notices a link to the body page
        
        #He then sees that there is information from other surveys that have already gotten spectra for his targets

        #Now knowing what he must do, Kildorn the Unstoppable takes a lunch break.
