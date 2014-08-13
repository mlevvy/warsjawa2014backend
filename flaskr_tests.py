# -*- coding: utf-8 -*-
import unittest
import flaskr
import mongomock
from mocker import MockerTestCase, MATCH


FIRST_NAME = "Jan"
LAST_NAME = "Kowalski"
EMAIL_ADDRESS = """jan@kowalski.com"""
REGISTRATION_REQUEST = """{"email":"%s", "firstName":"%s", "lastName": "%s"}""" % (EMAIL_ADDRESS, FIRST_NAME, LAST_NAME)
TEST_USER_IN_DB = {"email": EMAIL_ADDRESS, "firstName": FIRST_NAME, "lastName": LAST_NAME, "key": "TEST_KEY"}


class EmailsEndpointTest(MockerTestCase):
    def setUp(self):
        def get_db():
            return self.db

        self.app = flaskr.app.test_client()
        self.db = mongomock.Connection().db
        flaskr.get_db = get_db

    def test_should_add_new_email_to_database_and_send_email(self):
        # Given: Empty database
        self.mail_gun_should_receive(lambda d: d['to'] == EMAIL_ADDRESS and d['subject'] == "Hello")

        # When: Post to users
        rv = self.register_test_user()

        # Then response is OK
        self.assertEqual(rv.status_code, 201)
        self.assertEqual(rv.data, "")
        self.mocker.verify()

    def test_should_save_newly_registered_user_in_db(self):
        # Given: Empty database
        self.mail_gun_should_receive()

        # When: Post to users
        self.register_test_user()

        # Then response is OK
        self.assertEqual(self.db.users.count(), 1)
        self.assertEqual(self.db.users.find_one()["email"], EMAIL_ADDRESS)
        self.assertEqual(self.db.users.find_one()["firstName"], FIRST_NAME)
        self.assertEqual(self.db.users.find_one()["lastName"], LAST_NAME)
        self.assertEqual(self.db.users.find_one()["isConfirmed"], False)
        self.assertIsNotNone(self.db.users.find_one()["key"])

    def test_should_update_key_in_database_if_already_registered(self):
        # Given: database
        self.db.users.insert(TEST_USER_IN_DB)
        self.mail_gun_should_receive()

        # When: Post to users
        self.register_test_user()

        # Then response is OK
        self.assertEqual(self.db.users.count(), 1)
        user_in_db = self.db.users.find_one()
        self.assertDictContainsSubset({"email": EMAIL_ADDRESS, "firstName": FIRST_NAME, "lastName": LAST_NAME},
                                      user_in_db)
        self.assertIsNotNone(user_in_db["key"])

    def test_should_resend_email_with_new_key_if_is_not_confirmed(self):
        # Given: database
        self.db.users.insert(TEST_USER_IN_DB)

        self.mail_gun_should_receive(lambda d: d['to'] == EMAIL_ADDRESS and d['subject'] == "Hello")

        # When: Post to users
        self.register_test_user()

        # Then
        self.mocker.verify()

    def register_test_user(self):
        rv = self.app.post('/users', data=REGISTRATION_REQUEST, content_type="application/json")
        return rv

    def mail_gun_should_receive(self, data_validator=lambda d: True):
        result = self.mocker.mock()
        mock_post = self.mocker.replace("requests.post")
        mock_post('https://api.mailgun.net/v2/system.warsjawa.pl/messages',
               auth=('api', None),
               data=MATCH(data_validator)
        )
        self.mocker.result(result)
        self.mocker.replay()


if __name__ == '__main__':
    unittest.main()
