import django_filters

from core.models import Block, Frame

class FrameFilter(django_filters.FilterSet):

    class Meta:
        model = Frame
        fields = ('filename', 'frametype')


class BlockFilter(django_filters.FilterSet):

    tracking_number = django_filters.CharFilter(
        field_name='superblock__tracking_number', lookup_expr='icontains',
        label='Tracking Number', distinct=True
    )
    class Meta:
        model = Block
        fields = ('tracking_number', 'obstype')
