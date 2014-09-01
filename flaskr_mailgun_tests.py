import unittest
import datetime
from unittest.mock import patch

from flaskr_tests import FlaskrWithMongoTest, assert_mailgun
from flaskr_users_tests import EMAIL_ADDRESS as USER_EMAIL_ADDRESS

WORKSHOP_ID = "test_workshop"
WORKSHOP_EMAIL_SECRET = "tajny-kod"

CURRENT_DATE = datetime.datetime(2007, 12, 6, 16, 29, 43, 79043)

WORKSHOP_IN_DB = {
    "workshopId": WORKSHOP_ID,
    "emailSecret": WORKSHOP_EMAIL_SECRET,
    "mentors": [
        "jan@kowalski.pl",
        "adam@nowak.pl"
    ],
    "users": [
        USER_EMAIL_ADDRESS
    ],
    "emails": [
    ]
}

EXAMPLE_MAILGUN_POST = {
    'from': 'Jan Kowalski <jan@kowalski.com>',
    'to': 'Warsjawa',
    'subject': 'test',
    'recipient': 'test-workshop-%s@system.warsjawa.pl' % WORKSHOP_EMAIL_SECRET,
    'body-plain': 'text',
    'body-html': 'text'
}


class MailgunEndpointTest(FlaskrWithMongoTest, unittest.TestCase):
    @patch('mailgunresource.requests')
    def test_should_save_incoming_emails_in_workshop_and_forward_to_users(self, requests_mock):
        # Given a database with one workshop
        self.db.workshops.insert(WORKSHOP_IN_DB)

        # When
        rv = self.mailgun_sends_email()

        # Then
        self.assertEqual(1, len(self.db.workshops.find_one()['emails']))
        assert_mailgun(requests_mock, to=USER_EMAIL_ADDRESS, subject="test")

    def mailgun_sends_email(self):
        rv = self.app.post('/mailgun', data=EXAMPLE_MAILGUN_POST)
        return rv


if __name__ == '__main__':
    unittest.main()
