"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2015-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from sys import argv
from datetime import datetime, timedelta
from io import StringIO

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.core import serializers
import tablib

from core.models import *
from core.admin import FrameResource, SourceMeasResource, CatalogResource

class Command(BaseCommand):

    """
    Import content following relationships. Run this after you have run export_test_fixtures on server and downloaded contents of
    core/fixtures/
    A fresh, migrated database is needed to first ie.:
    ./manage.py migrate; ./manage.py import_test_fixtures
    """

    help = 'Import content following relationships'

    def handle(self, **options):
        # Export the smaller tables in full
        self.stdout.write("Loading standard fixtures...")
        call_command('loaddata', 'partial.json')
        self.stdout.write("Successfully loaded fixtures")

        names = [
            'frames',
            'sourcemeas',
            'catalogsources'
        ]
        for name in names:
            with open('core/fixtures/{}.xml'.format(name),'r') as f:
                for deserialized_object in serializers.deserialize("xml", f):
                    deserialized_object.save()
                self.stdout.write("Imported {}".format(name))
