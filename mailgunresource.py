import requests
import os


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
    return requests.post \
        ("https://api.mailgun.net/v2/system.warsjawa.pl/messages",
         auth=("api", os.environ.get('MAILGUN_API_KEY')),
         **kwargs
        )
