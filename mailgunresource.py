import os
import logging
import requests


logger = logging.getLogger('mailgun')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(ch)


def send_add_new_user(user_registration):
    return send_mail(user_registration['email'], "Hello", "Lorem Ipsum")


def send_deny_new_user(user_registration):
    return send_mail(user_registration['email'], "We've got a problem here !", "Lorem Ipsum")


def send_confirm_user(user_registration):
    return send_mail(user_registration['email'], "You are confirmed now", "Lorem Ipsum")


def send_deny_confirm_user(user_registration):
    return send_mail(user_registration['email'], "You can not confirm twice", "Lorem Ipsum")


def send_workshop_mail(user_mail, subject, text):
    return send_mail(user_mail, subject, text)


def send_mail(to, subject, text):
    return send_mail_raw(
        data={"from": "Warsjawa <postmaster@system.warsjawa.pl>", "to": to, "subject": subject, "text": text}
    )


def send_mail_raw(**kwargs):
    mailgun_result = requests.post("https://api.mailgun.net/v2/system.warsjawa.pl/messages",
                                   auth=("api", os.environ.get('MAILGUN_API_KEY')), **kwargs)
    logger.debug("Mailgun %3d: %s, %s", mailgun_result.status_code, kwargs, mailgun_result)
    return mailgun_result
