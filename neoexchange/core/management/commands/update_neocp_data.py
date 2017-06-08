from django.core.management.base import BaseCommand, CommandError

from core.tasks import update_neocp_data


class Command(BaseCommand):
    help = 'Check NEOCP for objects in need of follow up'

    def handle(self, *args, **options):
        update_neocp_data()
