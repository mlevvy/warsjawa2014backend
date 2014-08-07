# -*- coding: utf-8 -*-
import unittest
import flaskr
import mongomock

# TODO Change assert order

class EmailsEndpointTest(unittest.TestCase):
    def setUp(self):
        def get_db():
            return self.db
        self.app = flaskr.app.test_client()
        self.db = mongomock.Connection().db
        flaskr.get_db = get_db

    def test_should_add_new_email_to_database_and_send_email(self):
        # Given: Empty database
        input_request = """{"email":"tomek@nurkiewicz", "firstName":"Tomek", "lastName": "Nurkiewicz"}"""

        #When: Post to users
        rv = self.app.post('/users', data=input_request, content_type="application/json")

        #Then response is OK
        self.assertEqual(rv.status_code, 201)
        self.assertEqual(rv.data, "")
        self.assertEqual(self.db.users.count(), 1)
        self.assertEqual(self.db.users.find_one()["email"], "tomek@nurkiewicz")
        self.assertEqual(self.db.users.find_one()["firstName"], "Tomek")
        self.assertEqual(self.db.users.find_one()["lastName"], "Nurkiewicz")
        self.assertEqual(self.db.users.find_one()["isConfirmed"], False)
        self.assertIsNotNone(self.db.users.find_one()["key"])
        # TODO Assert mock mailgun

    def test_should_resend_email_with_new_key_if_is_not_confirmed(self):
        # Given: database
        self.db.users.insert({"email":"tomek@nurkiewicz", "firstName":"Tomek", "lastName": "Nurkiewicz", "key": "TEST_KEY"})
        input_request = """{"email":"tomek@nurkiewicz", "firstName":"Tomek", "lastName": "Nurkiewicz"}"""

        #When: Post to users
        rv = self.app.post('/users', data=input_request, content_type="application/json")

        #Then response is OK
        self.assertEqual(rv.status_code, 201)
        self.assertEqual(rv.data, "")
        self.assertEqual(self.db.users.count(), 1)
        self.assertEqual(self.db.users.find_one()["email"], "tomek@nurkiewicz")
        self.assertEqual(self.db.users.find_one()["firstName"], "Tomek")
        self.assertEqual(self.db.users.find_one()["lastName"], "Nurkiewicz")
        self.assertIsNotNone(self.db.users.find_one()["key"])
        # TODO Assert mock mailgun



if __name__ == '__main__':
    unittest.main()