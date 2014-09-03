import binascii
import os
import string

from pymongo.son_manipulator import SONManipulator
import yaml

import mailgunresource


def read_templates():
    f = open("emails.yml", encoding="utf-8")
    return yaml.load(f)


templates = read_templates()


def generate_email_id():
    return binascii.hexlify(os.urandom(32)).decode('UTF-8')


def substitute_variables(template, data):
    return string.Template(template).safe_substitute(**data)


class MailMessageCreator():
    @classmethod
    def user_registration(cls, user_name, user_key):
        template = templates["user_registration"]
        data = {
            'name': user_name,
            'userCode': user_key
        }
        return EmailMessage(
            sender='Warsjawa <contact@warsjawa.pl>',
            subject=substitute_variables(template['subject'], data),
            text=substitute_variables(template['body-plain'], data),
            html=substitute_variables(template['body-html'], data)
        )

    @classmethod
    def user_confirmation(cls, user_name, user_key):
        template = templates["user_confirmation"]
        data = {
            'name': user_name,
            'userCode': user_key
        }
        return EmailMessage(
            sender='Warsjawa <contact@warsjawa.pl>',
            subject=substitute_variables(template['subject'], data),
            text=substitute_variables(template['body-plain'], data),
            html=substitute_variables(template['body-html'], data)
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
            html=substitute_variables(template['body-html'], data),
            date = mentor_message.date
        )


class EmailMessage():
    def __init__(self, sender, subject, text, html=None, date=None, files=None, raw_message=None, email_id=None):
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
        return EmailMessage(**value)


class Transform(SONManipulator):
    def transform_incoming(self, son, collection):
        for (key, value) in son.items():
            if isinstance(value, EmailMessage):
                son[key] = value.as_db_dict()
            elif isinstance(value, dict):
                son[key] = self.transform_incoming(value, collection)
        return son

    def transform_outgoing(self, son, collection):
        for (key, value) in son.items():
            if isinstance(value, dict):
                if "_type" in value and value["_type"] == "EmailMessage":
                    son[key] = EmailMessage.from_db_dict(value)
                else:
                    son[key] = self.transform_outgoing(value, collection)
        return son

