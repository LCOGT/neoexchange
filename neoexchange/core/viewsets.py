from rest_framework import serializers, viewsets, generics
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend

from core.models import Proposal, SuperBlock, Block, Frame, CatalogSources, Body, \
    SourceMeasurement
from core.views import user_proposals
from core.filters import SuperBlockFilter, BlockFilter, FrameFilter, CatalogSourcesFilter, \
    BodyFilter, SourceMeasurementFilter


class ProposalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proposal
        exclude = ('id',)


class SuperBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuperBlock
        fields = '__all__'


class BlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Block
        fields = '__all__'


class FrameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Frame
        exclude = ('wcs', )
        read_only_fields = (
            'id',
        )


class CatalogSourcesSerializer(serializers.ModelSerializer):
    class Meta:
        model = CatalogSources
        fields = '__all__'


class BodySerializer(serializers.ModelSerializer):
    class Meta:
        model = Body
        fields = '__all__'


class SourceMeasurementSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceMeasurement
        fields = '__all__'


class ProposalViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Proposal.objects.filter(download=True, active=True)
    serializer_class = ProposalSerializer


class SuperBlockViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticatedOrReadOnly,)
    http_method_names = ['get', 'head', 'options']
    serializer_class = SuperBlockSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = SuperBlockFilter
    queryset = SuperBlock.objects.all()


class BlockViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticatedOrReadOnly,)
    http_method_names = ['get', 'head', 'options']
    serializer_class = BlockSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = BlockFilter

    def get_queryset(self):
        qs = Block.objects.all()

        return qs


class FrameViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticatedOrReadOnly,)
    http_method_names = ['get', 'head', 'options']
    serializer_class = FrameSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = FrameFilter

    def get_queryset(self):
        if self.request.user.is_staff:
            qs = Frame.objects.all()
        elif self.request.user.is_authenticated:
            qs = Frame.objects.filter(
                block__superblock__proposal__in=user_proposals(self.request.user)
            )
        else:
            qs = Frame.objects.filter(frametype__in=[Frame.NONLCO_FRAMETYPE, Frame.SATELLITE_FRAMETYPE])
        return qs


class CatalogSourcesViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    http_method_names = ['get', 'post', 'head', 'options']
    serializer_class = CatalogSourcesSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = CatalogSourcesFilter
    queryset = CatalogSources.objects.all()

    def perform_create(self, serializer):
        serializer.save()


class BodyViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticatedOrReadOnly,)
    http_method_names = ['get', 'head', 'options']
    serializer_class = BodySerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = BodyFilter

    def get_queryset(self):
        qs = Body.objects.all()

        return qs


class SourceMeasurementViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    http_method_names = ['get', 'post', 'put', 'head', 'options']
    serializer_class = SourceMeasurementSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = SourceMeasurementFilter
    queryset = SourceMeasurement.objects.all()
