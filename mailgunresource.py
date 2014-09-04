import datetime
import os
import logging
from flask import g

import requests


logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
logger = logging.getLogger('mailgun')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(ch)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

import http.client as http_client

http_client.HTTPConnection.debuglevel = 1


def send_deny_new_user(user_registration):
    return send_mail(user_registration['email'], "We've got a problem here !", "Lorem Ipsum")


def send_deny_confirm_user(user_registration):
    return send_mail(user_registration['email'], "You can not confirm twice", "Lorem Ipsum")


def send_mail(to, subject, text):
    return send_mail_raw(
        data={"from": "Warsjawa <postmaster@system.warsjawa.pl>", "to": to, "subject": subject, "text": text}
    )


def send_mail_raw(**kwargs):
    mailgun_result = requests.post("https://api.mailgun.net/v2/system.warsjawa.pl/messages",
                                   auth=("api", os.environ.get('MAILGUN_API_KEY')), **kwargs)
    logger.debug("Mailgun %3d: %s, %s, %s", mailgun_result.status_code, kwargs, mailgun_result, mailgun_result.text)
    if mailgun_result.status_code != 200 and hasattr(g, 'db'):
        g.db.mail_errors.insert({
            'request': kwargs,
            'result': {
                'status_code': mailgun_result.status_code,
                'text': mailgun_result.text
            },
            'date': datetime.datetime.now()
        })
    return mailgun_result
