from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from core.models import Proposal, Frame


class ProposalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proposal
        exclude = ('id',)

class FrameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Frame
        fields = '__all__'
        read_only_fields = (
            'id',
        )

class ProposalViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Proposal.objects.filter(download=True, active=True)
    serializer_class = ProposalSerializer

class FrameViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticatedOrReadOnly,)
    http_method_names = ['get', 'head', 'options']
    serializer_class = FrameSerializer
    def get_queryset(self):
        if self.request.user.is_staff:
            qs = Frame.objects.all()
        elif self.request.user.is_authenticated:
            qs = Frame.objects.filter(
                proposal__in=self.request.user.proposal_set.all()
            )
        else:
            qs = Frame.objects.filter(frametype__in=[Frame.NONLCO_FRAMETYPE, Frame.SATELLITE_FRAMETYPE])
        return qs
