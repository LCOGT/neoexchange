import django_filters

from core.models import Block, Frame

class FrameFilter(django_filters.FilterSet):

    class Meta:
        model = Frame
        fields = ('filename', 'frametype')


class BlockFilter(django_filters.FilterSet):

    class Meta:
        model = Block
        fields = ('tracking_number', 'obstype')
