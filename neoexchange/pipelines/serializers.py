import os.path

from django.shortcuts import reverse
from django.contrib.sites.shortcuts import get_current_site
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from core.models import AsyncProcess, PipelineProcess


class TimestampField(serializers.Field):
    def to_representation(self, dt):
        return dt.timestamp()


class AsyncProcessSerializer(serializers.ModelSerializer):
    created = TimestampField()
    terminal_timestamp = TimestampField()
    failure_message = serializers.SerializerMethodField()

    class Meta:
        model = AsyncProcess
        fields = [
            'identifier', 'created', 'status', 'terminal_timestamp', 'failure_message',
            'process_type'
        ]

    def get_failure_message(self, obj):
        return obj.failure_message or None


class PipelineProcessSerializer(AsyncProcessSerializer):
    logs = serializers.SerializerMethodField()

    class Meta:
        model = PipelineProcess
        fields = [
            'identifier', 'created', 'status', 'terminal_timestamp', 'failure_message',
            'logs'
        ]

    def get_logs(self, obj):
        """
        Make sure logs is always a string
        """
        return obj.logs or ''
