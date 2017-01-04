from django.template.loader import get_template
from django.template import Context
from django.core.mail import send_mail
from django.conf import settings

from core.views import measurements_from_block
from core.models import Block

def email_report_to_mpc(blockid):
    message = get_template('core/mpc_email.txt')
    data = measurements_from_block(blockid)
    message.render(Context(data))
    print(t)
    try:
        send_mail(
            'Subject here',
            message,
            settings.,
            ['to@example.com'],
            fail_silently=False,
        )
    except:
        return False
    return True

def report_to_mpc():
    return
