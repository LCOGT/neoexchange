from django.template.loader import get_template
from django.template import Context
from django.core.mail import send_mail
from django.conf import settings

from core.frames import measurements_from_block

def generate_message(blockid):
    t = get_template('core/mpc_email.txt')
    data = measurements_from_block(blockid)
    message = t.render(Context(data))

    return message

def email_report_to_mpc(blockid):

    message = generate_message(blockid)
    try:
        send_mail(
            'MPC submission test',
            message,
            settings.DEFAULT_FROM_EMAIL,
            ['egomez@lco.global'],
            fail_silently=False,
        )
    except Exception, e:
        print(e)
        return False
    return True
