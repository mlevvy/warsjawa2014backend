import unittest
from unittest.mock import patch

from flaskr_tests import FlaskrWithMongoTest, assert_mailgun, EXAMPLE_MAILGUN_POST, SECOND_MAIL_SUBJECT, \
    EMAIL_ADDRESS as USER_EMAIL_ADDRESS, workshop_in_db, user_in_db


class MailgunEndpointTest(FlaskrWithMongoTest, unittest.TestCase):
    @patch('mailgunresource.requests')
    def test_should_save_incoming_emails_in_workshop_and_forward_to_users(self, requests_mock):
        # Given a database with one workshop
        self.db.workshops.insert(workshop_in_db(with_user=True, with_mail=False))
        self.db.users.insert(user_in_db(confirmed=True))

        # When
        rv = self.mailgun_sends_email()

        # Then
        self.assertEqual(1, len(self.db.workshops.find_one()['emails']))
        self.assertEqual(1, requests_mock.post.call_count)
        assert_mailgun(requests_mock, to=USER_EMAIL_ADDRESS, subject=SECOND_MAIL_SUBJECT)

    def mailgun_sends_email(self):
        rv = self.app.post('/mailgun', data=EXAMPLE_MAILGUN_POST)
        return rv


if __name__ == '__main__':
    unittest.main()
