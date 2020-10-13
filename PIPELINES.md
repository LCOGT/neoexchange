# Creating a new pipeline

## Sandbox Installation
To run asynchronous tasks you will need a message broker and queue handler. We will use `Dramatiq` and `redis` for these. `django-dramatiq` is already in `requirements.txt` so make sure you install it in your environment.

`redis` is a fast and simple key-value database. You'll need to install this on your system, either with a package manager or from source.

## Configuration
The purpose of this guide is to setup asynchronous, long running tasks, which would normally cause the browser to timeout.

### Tasks

All asynchronous tasks are handled by `core/tasks.py`  so that you don't have to configure this with each new pipeline, you can just include a pipeline in `settings.py`.

```
PIPELINES = {
  # 'shortname' : 'PATH TO MYPIPELINE CLASS'
  'mypipe' : 'pipelines.mypipe.MyPipeline',
}
```

### Pipeline models

Each pipeline model subclasses `core.models.pipelines.PipelineProcess`.

Depending on how extensive your pipeline code is, you may want to create it as a seperate app inside the NEOexchange Django project or inside the `pipelines` app (if you are calling existing code, this is the simplest way).


Then create `mypipe.py` in the `pipelines` app.

```
from core.models.pipelines import PipelineProcess
from core.utils import NeoException
from anotherapp.utils import data_analysis


class MyPipeline(PipelineProcess):
    """
    Download and process FITS image and spectra data
    """
    short_name = 'myp' # Used for as prefix for the log messages

    # Input parameters, these are form parameters passed to the pipeline from frontend
    inputs = {
        'obs_date': {
            'default': None,
            'long_name': 'Date of the data to download (YYYYMMDD)'
        },
        'beans' : {
          'default' : 5,
          'long_name' : 'Number of beans which make 5'
        }
      }

    class Meta:
        proxy = True

    # Override this function in the base class    
    def do_pipeline(self, **inputs):

        try:
            # Here you call all the  
            values = data_analysis(**inputs)
        except NeoException as ex:
            msg = 'Error with data analysis'
            logger.error(f'{msg}: {ex}')
            self.log(f'{msg}: {ex}')
            raise AsyncError(f'{msg}')
        except TimeLimitExceeded:
            raise AsyncError("MyPipe took longer than 10 mins to create")
        except PipelineProcess.DoesNotExist:
            raise AsyncError("Record has been deleted")
        self.log('Pipeline Completed')
        return
```

### Form

Add a form to handle any inputs and to start the pipeline. If you are using the `pipelines` app, update the `forms.py` to include the new form class or you can process any form input yourself in a view.

```
```

```
class MySubmitView(PipelineSubmitView):
    template_name = 'pipelines/mypipe_form.html'
    form_class = MyPipe
    name = 'mypipe' # Pipeline name in settings.py
    title = 'Count how many beans make 5 asteroids' # page title for form
```
