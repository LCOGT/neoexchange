import logging
from datetime import datetime

from django.forms import model_to_dict
from dramatiq.middleware.time_limit import TimeLimitExceeded

from astrometrics.ephem_subs import monitor_long_term_scheduling
from core.models import Body
from core.models.pipelines import PipelineProcess, PipelineOutput
from core.utils import save_to_default, NeoException

logger = logging.getLogger(__name__)

class LongTermEphemeris(PipelineProcess):
    """
    Compute a long term ephemeris
    """
    short_name = 'ephem'
    inputs = {
        'start_date': {
            'default': None,
            'long_name': 'Start date of the ephemeris (YYYYMMDD)'
        },
        'end_date': {
            'default': None,
            'long_name': 'End date of the ephemeris (YYYYMMDD)'
        },
        'body' : {
            'default' : None,
            'long_name' : 'Body id (PK) to compute the ephemeris for'
        }
    }    
    class Meta:
        proxy = True

    def do_pipeline(self, tmpdir, **inputs):
        start_date = inputs.get('start_date')
        end_date = inputs.get('end_date')
        body = inputs.get('body')

        try:
            self.compute(body, start_date, end_date)
        except NeoException as ex:
            logger.error('Error with ephemeris generation: {}'.format(ex))
            self.log('Error with ephemeris generation: {}'.format(ex))
            raise AsyncError('Error creating ephemeris generation')
        except TimeLimitExceeded:
            raise AsyncError("Ephemeris generation took longer than 10 mins to create")
        except PipelineProcess.DoesNotExist:
            raise AsyncError("Record has been deleted")
        self.log('Pipeline Completed')
        return

    def compute(self, obj_id, start_date, end_date, site_code='V37'):
        orbelems = model_to_dict(Body.objects.get(pk=obj_id))
        date_range = end_date - start_date
        visible_dates, emp_visible_dates, dark_and_up_time_all, max_alt_all = monitor_long_term_scheduling(site_code, orbelems, start_date, date_range.days, 1.0)
