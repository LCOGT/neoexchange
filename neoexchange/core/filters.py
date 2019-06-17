import django_filters

from core.models import Frame

class FrameFilter(django_filters.FilterSet):

    class Meta:
        model = Frame
        fields = ('filename', 'frametype')
