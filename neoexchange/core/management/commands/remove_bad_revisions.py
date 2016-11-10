from core.models import Body
from reversion.models import Version

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count
from django.forms.models import model_to_dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Update objects for new cross-identifications from the Previous NEO Confirmation Page Objects page'

    def handle(self, *args, **options):
        self.stdout.write("==== Removing Bad Revisions %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        bodies = Version.objects.filter(content_type=15).values('object_id').annotate(sum=Count('id')).order_by('-sum')
        num_d = 0
        num_s = 0
        for body in bodies:
            logger.debug('*** Inspecting Body ID {} ***'.format(body['object_id']))
            versions = Version.objects.filter(object_id=body['object_id']).order_by('revision__date_created')
            if versions.count() <= 2:
                continue
            original = versions.first()
            for version in versions[1:]:
                update = False
                fields = ['slope', 'origin', 'epochofel', 'abs_mag', 'arc_length', 'orbinc', 'source_type', 'longascnode', 'eccentricity', 'argofperih', 'discovery_date', 'meandist', 'elements_type', 'meananom','name','provisional_name','provisional_packed']
                vers_dict = version.field_dict
                orig_dict = original.field_dict
                # Check if the values in the original are the same as the revision
                for k in fields:
                    try:
                        if vers_dict[k] != orig_dict[k]:
                            update = True
                    except KeyError, e:
                        logger.debug('Error with {}'.format(e))
                if update:
                    original = version
                    #logger.debug('Saved version {}'.format(version.id))
                    num_s += 1
                else:
                    #logger.debug('Deleted version {}'.format(version.id))
                    version.revision.delete()
                    version.delete()
                    num_d += 1
        logger.debug("Updated: {} bodies".format(bodies.count()))
        logger.debug("Deleted: {} revisions".format(num_d))
        logger.debug("Saved: {} revisions".format(num_s))
