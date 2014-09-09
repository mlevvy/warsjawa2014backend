import binascii
import datetime
import os
import string
from urllib.parse import quote_plus as escape_uri

import yaml

import mailgunresource

WARSJAVA_SENDER_EMAIL = 'Warsjawa <contact@warsjawa.pl>'


def read_templates():
    f = open("emails.yml", encoding="utf-8")
    return yaml.load(f)


templates = read_templates()


def generate_email_id():
    return binascii.hexlify(os.urandom(32)).decode('UTF-8')


def substitute_variables(template, data):
    return string.Template(template).safe_substitute(**data)


def create_email_address_for_workshop(email_secret):
    return "workshop-%s@system.warsjawa.pl" % email_secret


class MailMessageCreator():
    @classmethod
    def user_registration(cls, user_name, user_key, user_email):
        template = templates["user_registration"]
        data = {
            'name': user_name,
            'userCode': user_key,
            'userEmail': escape_uri(user_email)
        }
        return EmailMessage(
            sender=WARSJAVA_SENDER_EMAIL,
            subject=substitute_variables(template['subject'], data),
            text=substitute_variables(template['body-plain'], data),
            html=substitute_variables(template['body-html'], data),
            date=datetime.datetime.now()
        )

    @classmethod
    def user_confirmation(cls, user_name, user_key, user_email):
        template = templates["user_confirmation"]
        data = {
            'name': user_name,
            'userCode': user_key,
            'userEmail': escape_uri(user_email)
        }
        return EmailMessage(
            sender=WARSJAVA_SENDER_EMAIL,
            subject=substitute_variables(template['subject'], data),
            text=substitute_variables(template['body-plain'], data),
            html=substitute_variables(template['body-html'], data),
            date=datetime.datetime.now()
        )

    @classmethod
    def forward_workshop_message(cls, mentor_message, workshop):
        template = templates["workshop_mail"]
        data = {
            'workshopName': workshop['name'] if 'name' in workshop else workshop['workshopId'],
            'originalSubject': mentor_message.subject,
            'plainEmailBody': mentor_message.text,
            'htmlEmailBody': mentor_message.html
        }
        return EmailMessage(
            sender=mentor_message.sender,
            subject=substitute_variables(template['subject'], data),
            text=substitute_variables(template['body-plain'], data),
            html=(substitute_variables(template['body-html'], data) if data['htmlEmailBody'] is not None else None),
            date=mentor_message.date
        )

    @classmethod
    def mentor_welcome_email(cls, workshop_name, email_secret):
        template = templates["mentor_welcome"]
        data = {
            'workshopName': workshop_name,
            'workshopEmail': create_email_address_for_workshop(email_secret)
        }
        return EmailMessage(
            sender=WARSJAVA_SENDER_EMAIL,
            subject=substitute_variables(template['subject'], data),
            text=substitute_variables(template['body-plain'], data),
            html=substitute_variables(template['body-html'], data),
            date=datetime.datetime.now()
        )


class EmailMessage():
    def __init__(self, subject, text, sender=None, html=None, date=None, files=None, raw_message=None, email_id=None):
        self.email_id = email_id
        self.sender = sender
        self.subject = subject
        self.text = text
        self.html = html
        self.date = date
        self.files = files
        self.raw_message = raw_message

    def as_request_to_send(self, recipient):
        return {
            'to': recipient,
            'from': self.sender,
            'subject': self.subject,
            'text': self.text,
            'html': self.html
        }

    def as_db_dict(self):
        return {
            'from': self.sender,
            'subject': self.subject,
            'text': self.text,
            'html': self.html,
            'date': self.date,
            'files': self.files,
            'raw_message': self.raw_message,
            'email_id': self.email_id,
            '_type': "EmailMessage"
        }

    def as_response(self):
        return {
            'from': self.sender,
            'subject': self.subject,
            'text': self.text,
            'date': self.date
        }

    def send(self, to):
        mailgunresource.send_mail_raw(
            data=self.as_request_to_send(recipient=to)
        )

    @classmethod
    def from_db_dict(cls, value):
        if isinstance(value, EmailMessage):
            return value
        elif isinstance(value, dict):
            attrs = {k: value[k] for k in
                     ["sender", "subject", "text", "html", "date", "files", "raw_message", "email_id"] if k in value}
            return EmailMessage(**attrs)
        else:
            raise AttributeError("Invalid value: %s of type %s" % (value, type(value)))
