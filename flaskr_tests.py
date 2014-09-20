# -*- coding: utf-8 -*-
import datetime
import unittest

import mongomock
from emails import EmailMessage

import flaskr


NAME = "Jan Kowalski"
EMAIL_ADDRESS = "jan@kowalski.com"
TEST_KEY = "TEST_KEY"
FIRST_MAIL_SUBJECT = "Introduction to test workshop"
SECOND_MAIL_SUBJECT = "Link to repository"
WORKSHOP_ID = "test_workshop"
WORKSHOP_EMAIL_SECRET = "tajny-kod"
CURRENT_DATE = datetime.datetime(2007, 12, 6, 16, 29, 43, 79043)
EMAIL_MESSAGE = EmailMessage(FIRST_MAIL_SUBJECT, "text", sender="source@example.com", date=CURRENT_DATE, email_id=1)


def user_in_db(confirmed=False, email=EMAIL_ADDRESS, **kwargs):
    user = {
        "email": email,
        "name": NAME,
        "key": TEST_KEY,
        "isConfirmed": confirmed,
        "emails": []
    }
    user.update(kwargs)
    return user


def workshop_in_db(with_user, with_mail):
    return {
        "workshopId": WORKSHOP_ID,
        "emailSecret": WORKSHOP_EMAIL_SECRET,
        "name": "Workshop Name",
        "mentors": [
        ],
        "users": [EMAIL_ADDRESS] if with_user else [],
        "emails": [EMAIL_MESSAGE] if with_mail else []
    }


EMAILS = {"emails": [{"from": "source@example.com", "subject": FIRST_MAIL_SUBJECT, "text": "text",
                      "date": "Thu, 06 Dec 2007 16:29:43 GMT"}]}

REGISTER_EMAIL_REQUEST = """{
            "subject": "%s",
            "text": "text"
        }""" % SECOND_MAIL_SUBJECT

EXAMPLE_MAILGUN_POST = {
    'from': 'Jan Kowalski <jan@kowalski.com>',
    'to': 'Warsjawa',
    'subject': SECOND_MAIL_SUBJECT,
    'recipient': 'test-workshop-%s@system.warsjawa.pl' % WORKSHOP_EMAIL_SECRET,
    'body-plain': 'text',
    'body-html': 'text'
}


class FlaskrWithMongoTest():
    def setUp(self):
        def get_db():
            return self.db

        self.app = flaskr.app.test_client()
        self.db = mongomock.Connection().db
        flaskr.get_db = get_db


def assert_mailgun(requests_mock, to=None, subject=None):
    ((mailgun_url, ), mailgun_attrs) = requests_mock.post.call_args
    assert "https://api.mailgun.net/v2/system.warsjawa.pl/messages" == mailgun_url
    if to is not None:
        assert to == mailgun_attrs['data']['to']
    if subject is not None:
        assert subject == mailgun_attrs['data']['subject']


if __name__ == '__main__':
    unittest.main()
