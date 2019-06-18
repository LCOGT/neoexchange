import django_filters

from core.models import SuperBlock, Block, Frame


class SuperBlockFilter(django_filters.FilterSet):

    blockstart_before = django_filters.DateTimeFilter(field_name='block_start', lookup_expr='lte', label='Block start before')
    blockstart_after = django_filters.DateTimeFilter(field_name='block_start', lookup_expr='gte', label='Block start after')
    class Meta:
        model = SuperBlock
        fields = ('tracking_number', 'blockstart_before', 'blockstart_after')


class BlockFilter(django_filters.FilterSet):

    tracking_number = django_filters.CharFilter(
        field_name='superblock__tracking_number', lookup_expr='icontains',
        label='Tracking Number', distinct=True
    )
    class Meta:
        model = Block
        fields = ('tracking_number', 'obstype')


class FrameFilter(django_filters.FilterSet):

    class Meta:
        model = Frame
        fields = ('filename', 'frametype')
