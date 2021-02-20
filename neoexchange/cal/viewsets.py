from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import serializers, viewsets, generics, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly

from cal.models import CalEvent
from cal.filters import CalEventFilter
from cal.serializers import CalEventSerializer

class CalEventViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticatedOrReadOnly,)
    http_method_names = ['get', 'post', 'head', 'options']
    serializer_class = CalEventSerializer
    filter_class = CalEventFilter
    filter_backends = (
        filters.OrderingFilter,
        DjangoFilterBackend
    )
    ordering = ('-id',)

    def get_queryset(self):
        qs = CalEvent.objects.all()

        return qs

    def perform_create(self, serializer):
        serializer.save(submitter=self.request.user)
