# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch

from flaskr_tests import FlaskrWithMongoTest, assert_mailgun

# Example data
FIRST_NAME = "Jan"
LAST_NAME = "Kowalski"
EMAIL_ADDRESS = "jan@kowalski.com"
TEST_KEY = "TEST_KEY"

# Example request
REGISTRATION_REQUEST = """{"email":"%s", "firstName":"%s", "lastName": "%s"}""" % (EMAIL_ADDRESS, FIRST_NAME, LAST_NAME)
CONFIRMATION_REQUEST = """{"email":"%s", "key":"%s"}""" % (EMAIL_ADDRESS, TEST_KEY)

# Example database rows
TEST_NOT_CONFIRMED_USER_IN_DB = {
    "email": EMAIL_ADDRESS,
    "firstName": FIRST_NAME,
    "lastName": LAST_NAME,
    "key": TEST_KEY,
    "isConfirmed": False,
    "emails": []
}

TEST_CONFIRMED_USER_IN_DB = {
    "email": EMAIL_ADDRESS,
    "firstName": FIRST_NAME,
    "lastName": LAST_NAME,
    "key": TEST_KEY,
    "isConfirmed": True,
    "emails": []
}


class UsersEndpointTest(FlaskrWithMongoTest, unittest.TestCase):
    @patch('mailgunresource.requests')
    def test_should_send_email_and_return_correct_status_code(self, requests_mock):
        # Given: Empty database

        # When: Post to users
        rv = self.register_test_user()

        # Then response is OK
        self.assertEqual(rv.status_code, 201)
        assert_mailgun(requests_mock, to=EMAIL_ADDRESS)

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
        self.assertEqual(self.db.users.find_one()["emails"], [])
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
        assert_mailgun(requests_mock, EMAIL_ADDRESS, "We've got a problem here !")

    @patch('mailgunresource.requests')
    def test_should_resend_email_with_new_key_if_is_not_confirmed(self, requests_mock):
        # Given: database
        self.db.users.insert(TEST_NOT_CONFIRMED_USER_IN_DB)

        # When: Post to users
        self.register_test_user()

        # Then
        assert_mailgun(requests_mock, EMAIL_ADDRESS, "Hello")

    @patch('mailgunresource.requests')
    def test_should_deny_confirmation_by_sending_email_if_user_already_confirmed(self, requests_mock):
        # Given: database
        self.db.users.insert(TEST_CONFIRMED_USER_IN_DB)

        # When: Confirm user
        rv = self.confirm_test_user()

        # Then Return code is 304 and e-mail is sent
        self.assertEqual(rv.status_code, 304)
        assert_mailgun(requests_mock, EMAIL_ADDRESS, "You can not confirm twice")

    @patch('mailgunresource.requests')
    def test_should_deny_confirmation_by_not_changing_the_key_if_user_already_confirmed(self, requests_mock):
        # Given: database
        self.db.users.insert(TEST_CONFIRMED_USER_IN_DB)

        # When: Confirm user
        self.confirm_test_user()

        # Then Key is without change
        self.assertEqual(self.db.users.count(), 1)
        user_in_db = self.db.users.find_one()
        self.assertDictContainsSubset(
            {"email": EMAIL_ADDRESS, "firstName": FIRST_NAME, "lastName": LAST_NAME, "key": TEST_KEY,
             "isConfirmed": True},
            user_in_db)

    @patch('mailgunresource.requests')
    def test_should_deny_confirmation_if_user_is_not_found(self, requests_mock):
        # When: Confirm user
        rv = self.confirm_test_user()

        # Then Database is still empty
        self.assertEqual(self.db.users.count(), 0)

        self.assertEqual(rv.status_code, 404)

    @patch('mailgunresource.requests')
    def test_should_allow_confirmation_by_sending_email_if_user_is_not_confirmed(self, requests_mock):
        self.db.users.insert(TEST_NOT_CONFIRMED_USER_IN_DB)

        # When: Confirm user
        rv = self.confirm_test_user()

        # Then
        self.assertEqual(rv.status_code, 201)
        assert_mailgun(requests_mock, EMAIL_ADDRESS, "You are confirmed now")

    @patch('mailgunresource.requests')
    def test_should_allow_confirmation_by_changing_state_if_user_is_not_confirmed(self, requests_mock):
        self.db.users.insert(TEST_NOT_CONFIRMED_USER_IN_DB)

        # When: Confirm user
        self.confirm_test_user()

        # Then: User is confirmed
        self.assertEqual(self.db.users.count(), 1)
        user_in_db = self.db.users.find_one()
        self.assertDictContainsSubset(
            {"email": EMAIL_ADDRESS, "firstName": FIRST_NAME, "lastName": LAST_NAME, "key": TEST_KEY,
             "isConfirmed": True},
            user_in_db)

    def register_test_user(self):
        rv = self.app.post('/users', data=REGISTRATION_REQUEST, content_type="application/json")
        return rv

    def confirm_test_user(self):
        rv = self.app.put('/users', data=CONFIRMATION_REQUEST, content_type="application/json")
        return rv


if __name__ == '__main__':
    unittest.main()
