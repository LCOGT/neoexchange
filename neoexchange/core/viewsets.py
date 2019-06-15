from rest_framework import serializers, viewsets
from core.models import Proposal


class ProposalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proposal
        exclude = ('id',)


class ProposalViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Proposal.objects.filter(download=True, active=True)
    serializer_class = ProposalSerializer
