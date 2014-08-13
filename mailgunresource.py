import requests
import os


def send_registration_email(user_registration):
    return requests.post(
        "https://api.mailgun.net/v2/system.warsjawa.pl/messages",
        auth=("api", os.environ.get('MAILGUN_API_KEY')),
        data={"from": "Warsjawa <postmaster@system.warsjawa.pl>",
              "to": user_registration['email'],
              "subject": "Hello",
              "text": "Hello"})