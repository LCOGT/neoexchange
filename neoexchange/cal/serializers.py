import logging
from django.db import transaction
from rest_framework import serializers

from cal.models import CalEvent

logger = logging.getLogger(__name__)


class CalEventSerializer(serializers.ModelSerializer):

    submitter = serializers.StringRelatedField(default=serializers.CurrentUserDefault(), read_only=True)
    submitter_id = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = CalEvent
        fields = '__all__'
        read_only_fields = (
            'id', 'created', 'state', 'modified'
        )

    def create(self, validated_data):
        cal_event = CalEvent.objects.create(**validated_data)
        logger.info('CalEvent created', extra={'tags' : {'user' : cal_event.submitter.username,}})

        return cal_event

        
