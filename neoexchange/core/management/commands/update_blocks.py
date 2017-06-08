from django.core.management.base import BaseCommand, CommandError

from core.tasks import update_blocks


class Command(BaseCommand):
    help = 'Update pending blocks if observation requests have been made'

    def handle(self, *args, **options):
        update_blocks()
