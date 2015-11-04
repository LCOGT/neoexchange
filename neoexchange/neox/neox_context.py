from django.conf import settings

def neox_context_processor(request):
    my_dict = {
        'neox_version': settings.VERSION,
    }

    return my_dict
