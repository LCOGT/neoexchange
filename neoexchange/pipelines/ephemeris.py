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
        body = Body.objects.get(pk=obj_id)
        orbelems = model_to_dict(body)
        date_range = end_date - start_date
        self.log(f"Starting calculations for {body.current_name()}")
        visible_dates, emp_visible_dates, dark_and_up_time_all, max_alt_all = monitor_long_term_scheduling(site_code, orbelems, start_date, date_range.days, 1.0)
        self.log("Ephemeris for target {}".format(body.current_name()))
        self.log("Visible dates:")
        logger.critical(visible_dates)
        logger.critical(emp_visible_dates)
        logger.critical(dark_and_up_time_all)
        logger.critical(max_alt_all)
        for date in visible_dates:
            self.log(date)
        self.log("Start of night ephemeris entries for {}:".format(site_code))
        if len(emp_visible_dates) > 0:
            self.log('  Date/Time (UTC)        RA              Dec        Mag     "/min    P.A.    Alt Moon Phase Moon Dist Moon Alt Score  H.A.')
        for emp in emp_visible_dates:
            self.log("  ".join(emp))
        self.log("Maximum altitudes:")
        for x, alt in enumerate(max_alt_all):
            self.log("{}: {}".format(emp_visible_dates[x][0][0:10], alt))
        self.log("Number of hours target is up and sky is dark:")
        for x, time in enumerate(dark_and_up_time_all):
            self.log("{}: {}".format(emp_visible_dates[x][0][0:10], round(time, 2)))
        self.log("========================")
