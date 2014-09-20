import pprint
import unittest
from unittest.mock import patch

from flaskr_tests import FlaskrWithMongoTest, user_in_db, EMAIL_ADDRESS as USER_EMAIL_ADDRESS, workshop_in_db


VALID_RESULT_ADDRESSES = ["user2@example.com", "user12@example.com", "user20@example.com", "user21@example.com",
                          "user22@example.com"]


class ConfirmationEndpointTest(FlaskrWithMongoTest, unittest.TestCase):
    def test_should_mark_user_as_confirmed(self):
        self.db.users.insert(user_in_db(confirmed=True))

        self.app.get('/confirmation/%s' % USER_EMAIL_ADDRESS)

        self.assertEqual(self.db.users.find_one()['isConfirmedTwice'], True)

    def test_should_return_user_workshops(self):
        self.db.users.insert(user_in_db(confirmed=True))
        self.db.workshops.insert(workshop_in_db(with_user=True, with_mail=False))

        response = self.app.get('/confirmation/%s' % USER_EMAIL_ADDRESS)

        self.assertIn("text/html", response.content_type)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Workshop Name", pprint.pformat(response.get_data()))

    @patch('mailgunresource.send_mail_raw')
    def test_should_send_confirmation_email_to_users(self, mock):
        for i in range(23):
            self.db.users.insert(user_in_db(confirmed=True, email="user%d@example.com" % i))

        self.app.post('/confirmation/send?count=3&query=2')

        sent_email_addresses = [x[1]['data']['to'] for x in mock.call_args_list]
        self.assertEqual(len(sent_email_addresses), 3)
        for address in sent_email_addresses:
            self.assertIn(address, VALID_RESULT_ADDRESSES)


if __name__ == '__main__':
    unittest.main()
