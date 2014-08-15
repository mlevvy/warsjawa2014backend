# -*- coding: utf-8 -*-
import unittest
import flaskr
import mongomock
from unittest.mock import patch

FIRST_NAME = "Jan"
LAST_NAME = "Kowalski"
EMAIL_ADDRESS = "jan@kowalski.com"
TEST_KEY = "TEST_KEY"
REGISTRATION_REQUEST = """{"email":"%s", "firstName":"%s", "lastName": "%s"}""" % (EMAIL_ADDRESS, FIRST_NAME, LAST_NAME)
TEST_NOT_CONFIRMED_USER_IN_DB = {"email": EMAIL_ADDRESS, "firstName": FIRST_NAME, "lastName": LAST_NAME,
                                 "key": TEST_KEY, "isConfirmed": False}
TEST_CONFIRMED_USER_IN_DB = {"email": EMAIL_ADDRESS, "firstName": FIRST_NAME, "lastName": LAST_NAME, "key": TEST_KEY,
                             "isConfirmed": True}


class UsersEndpointTest(unittest.TestCase):
    def setUp(self):
        def get_db():
            return self.db

        self.app = flaskr.app.test_client()
        self.db = mongomock.Connection().db
        flaskr.get_db = get_db

    @patch('mailgunresource.requests')
    def test_should_send_email_and_return_correct_status_code(self, requests_mock):
        # Given: Empty database

        # When: Post to users
        rv = self.register_test_user()

        # Then response is OK
        self.assertEqual(rv.status_code, 201)
        ((mailgun_url, ), mailgun_attrs) = requests_mock.post.call_args
        self.assertEqual("https://api.mailgun.net/v2/system.warsjawa.pl/messages", mailgun_url)
        self.assertEqual(EMAIL_ADDRESS, mailgun_attrs['data']['to'])

    @patch('mailgunresource.requests')
    def test_should_save_newly_registered_user_in_db(self, requests_mock):
        # Given: Empty database

        # When: Post to users
        self.register_test_user()

        # Then row to database with random key is added
        self.assertEqual(self.db.users.count(), 1)
        self.assertEqual(self.db.users.find_one()["email"], EMAIL_ADDRESS)
        self.assertEqual(self.db.users.find_one()["firstName"], FIRST_NAME)
        self.assertEqual(self.db.users.find_one()["lastName"], LAST_NAME)
        self.assertEqual(self.db.users.find_one()["isConfirmed"], False)
        self.assertIsNotNone(self.db.users.find_one()["key"])

    @patch('mailgunresource.requests')
    def test_should_update_key_in_database_if_already_registered(self, requests_mock):
        # Given: database
        self.db.users.insert(TEST_NOT_CONFIRMED_USER_IN_DB)

        # When: Post to users
        self.register_test_user()

        # Then Key is changed
        self.assertEqual(self.db.users.count(), 1)
        user_in_db = self.db.users.find_one()
        self.assertDictContainsSubset({"email": EMAIL_ADDRESS, "firstName": FIRST_NAME, "lastName": LAST_NAME},
                                      user_in_db)
        self.assertIsNotNone(user_in_db["key"])
        self.assertIsNot(user_in_db["key"], TEST_KEY)

    @patch('mailgunresource.requests')
    def test_should_not_update_key_in_database_if_already_registered(self, requests_mock):
        # Given: database
        self.db.users.insert(TEST_CONFIRMED_USER_IN_DB)

        # When: Post to users
        self.register_test_user()

        # Then key is without change
        self.assertEqual(self.db.users.count(), 1)
        user_in_db = self.db.users.find_one()
        self.assertDictContainsSubset(
            {"email": EMAIL_ADDRESS, "firstName": FIRST_NAME, "lastName": LAST_NAME, "key": TEST_KEY},
            user_in_db)

    @patch('mailgunresource.requests')
    def test_should_send_deny_email_if_already_registered(self, requests_mock):
        # Given: database
        self.db.users.insert(TEST_CONFIRMED_USER_IN_DB)

        # When: Post to users
        rv = self.register_test_user()

        # Then key is without change
        self.assertEqual(rv.status_code, 304)
        ((mailgun_url, ), mailgun_attrs) = requests_mock.post.call_args
        self.assertEqual("https://api.mailgun.net/v2/system.warsjawa.pl/messages", mailgun_url)
        self.assertEqual(EMAIL_ADDRESS, mailgun_attrs['data']['to'])
        self.assertEqual("We've got a problem here !", mailgun_attrs['data']['subject'])

    @patch('mailgunresource.requests')
    def test_should_resend_email_with_new_key_if_is_not_confirmed(self, requests_mock):
        # Given: database
        self.db.users.insert(TEST_NOT_CONFIRMED_USER_IN_DB)

        # When: Post to users
        self.register_test_user()

        # Then
        ((mailgun_url, ), mailgun_attrs) = requests_mock.post.call_args
        self.assertEqual("https://api.mailgun.net/v2/system.warsjawa.pl/messages", mailgun_url)
        self.assertEqual(EMAIL_ADDRESS, mailgun_attrs['data']['to'])
        self.assertEqual("Hello", mailgun_attrs['data']['subject'])

    def register_test_user(self):
        rv = self.app.post('/users', data=REGISTRATION_REQUEST, content_type="application/json")
        return rv


if __name__ == '__main__':
    unittest.main()
