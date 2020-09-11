from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic.edit import FormView
from django.views.generic.detail import DetailView
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework import serializers
from rest_framework.response import Response


from core.models import PipelineProcess, AsyncProcess
from core.tasks import run_pipeline, send_task
from .forms import DLDataForm
from .serializers import AsyncProcessSerializer, PipelineProcessSerializer

class SubmitView(FormView):
    template_name = 'pipelines/pipeline_form.html'
    form_class = DLDataForm
    success_url = reverse_lazy('pipelines')

    def form_valid(self, form):
        return self.handle_pipeline(form)

    def handle_pipeline(self, form):
        name = 'dldata'
        try:
            pipeline_cls = PipelineProcess.get_subclass(name)
        except KeyError:
            return HttpResponseBadRequest("Invalid pipeline name '{}'".format(name))

        # Get pipeline-specific flags. Initially set all to False; those
        # present in form data will be set to True
        inputs = {f: False for f in pipeline_cls.inputs} if pipeline_cls.inputs else {}
        for key, value in form.cleaned_data.items():
            if key not in inputs:
                continue
            inputs[key] = value
        pipe = pipeline_cls.create_timestamped(inputs)
        send_task(run_pipeline, pipe, name)
        return redirect(self.success_url)
        # return JsonResponse({'ok': True})

def overview(request):
    pipelines = AsyncProcess.objects.all()
    return render(request, 'pipelines/overview.html', {'pipelines' : pipelines})

class AsyncStatusApi(ListAPIView):
    """
    View that finds all AsyncProcess objects associated with a specified Target
    and returns the listing in a JSON response
    """
    serializer_class = AsyncProcessSerializer

    def get_queryset(self):
        try:
            target = Target.objects.get(pk=self.kwargs['target'])
        except Target.DoesNotExist:
            raise Http404
        return AsyncProcess.objects.filter(target=target).order_by('-created')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        timestamp = TimestampField().to_representation(datetime.now())
        return Response({'timestamp': timestamp, 'processes': serializer.data})


class PipelineProcessDetailView(DetailView):
    model = PipelineProcess
    template_name = 'pipelines/pipeline_detail.html'


class PipelineProcessApi(RetrieveAPIView):
    """
    Return information about a PipelineProcess in a JSON response
    """
    queryset = PipelineProcess.objects.all()
    serializer_class = PipelineProcessSerializer
