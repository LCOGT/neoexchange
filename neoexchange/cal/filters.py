import django_filters

from cal.models import CalEvent


class CalEventFilter(django_filters.FilterSet):

    start_before = django_filters.DateTimeFilter(field_name='start', lookup_expr='lte', label='Event start before')
    start_after = django_filters.DateTimeFilter(field_name='start', lookup_expr='gte', label='Event start after')
    end_before = django_filters.DateTimeFilter(field_name='end', lookup_expr='lte', label='Event end before')
    end_after = django_filters.DateTimeFilter(field_name='end', lookup_expr='gte', label='Event end after')

    class Meta:
        model = CalEvent
        fields = ('event_type', 'state', 'start_before', 'start_after', 'end_before', 'end_after')
