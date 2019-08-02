from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings

# Media files are not public. Only authorized users should have access.
class PublicMediaStorage(S3Boto3Storage):
    location = 'data'
    default_acl = None
    file_overwrite = True
