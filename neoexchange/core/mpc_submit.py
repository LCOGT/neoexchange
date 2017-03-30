from django.template.loader import get_template
from django.template import Context
from django.core.mail import send_mail
from django.conf import settings

from core.frames import measurements_from_block

def generate_message(blockid, bodyid):
    t = get_template('core/mpc_email.txt')
    data = measurements_from_block(blockid,bodyid)
    message = t.render(Context(data))

    # Strip off last double newline but put one back again
    return message.rstrip() + '\n'

def email_report_to_mpc(blockid, bodyid, email_sender=None, receipients=['egomez@lco.global', 'tlister@lco.global']):
    if not bodyid:
        return False

    mpc_report = generate_message(blockid, bodyid)
    if email_sender == None:
        email_sender = settings.DEFAULT_FROM_EMAIL
# Do we need to test if the email_sender is in the recipient_list to prevent mail loops?
    try:
        send_mail(
            subject = 'MPC submission test',
            message = mpc_report,
            from_email = email_sender,
            recipient_list = receipients,
            fail_silently = False,
        )
    except Exception, e:
        print(e)
        return False
    return True
