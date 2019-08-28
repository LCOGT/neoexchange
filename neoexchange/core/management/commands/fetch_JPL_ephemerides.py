"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2019-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import boto3
from botocore.exceptions import ClientError


class Command(BaseCommand):
    help = 'Fetch JPL binary ephemeris from the S3 bucket'

    def handle(self, *args, **options):
        self.stdout.write("==== Fetching JPL ephemeris %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))

        if settings.USE_S3:
          
            client = boto3.client('s3',
                aws_access_key_id = settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY,
                region_name = settings.AWS_S3_REGION_NAME
            )
            params = {
                'Filename': '/ephemerides/jpleph.430',
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': 'ephemerides/linux_p1550p2650.430',
            }
            try:
                response = client.download_file(**params)
            except ClientError as e:
                self.stdout.write(e)

