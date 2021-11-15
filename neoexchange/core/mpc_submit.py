"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2014-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""
from django.template.loader import get_template
from django.core.mail import send_mail
from django.conf import settings

from core.frames import measurements_from_block


def generate_message(blockid, bodyid):
    t = get_template('core/mpc_email.txt')
    data = measurements_from_block(blockid, bodyid)
    message = t.render(data)

    # Strip off last double newline but put one back again
    return message.rstrip() + '\n'

def generate_ades_psv_message(blockid, bodyid, obs_filter=None):
    t = get_template('core/mpc_ades_psv.txt')
    data = measurements_from_block(blockid, bodyid, obs_filter)
    message = t.render(data)

    # Strip off last double newline but put one back again
    return message.rstrip() + '\n'

def email_report_to_mpc(blockid, bodyid, email_sender=None, recipients=settings.EMAIL_MPC_RECIPIENTS):
    if not bodyid:
        return False

    mpc_report = generate_message(blockid, bodyid)
    if email_sender is None:
        email_sender = settings.DEFAULT_FROM_EMAIL
# Do we need to test if the email_sender is in the recipient_list to prevent mail loops?
    try:
        send_mail(
            subject = 'MPC submission test',
            message = mpc_report,
            from_email = email_sender,
            recipient_list = recipients,
            fail_silently = False,
        )
    except Exception as e:
        print(e)
        return False
    return True
