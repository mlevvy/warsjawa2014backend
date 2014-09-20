import unittest

from flask import json

from unittest.case import SkipTest
from flaskr import find_user_for_tag

from flaskr_tests import FlaskrWithMongoTest, user_in_db, EMAIL_ADDRESS as USER_EMAIL_ADDRESS

NFC_TAG_ID = "TAG_ID"
VOTE_POSITIVE_REQUEST = """{
"mac":"MAC",
"tagId": "TAG_ID",
"isPositive": true,
"timestamp": "2014-09-18T10:32:59+00:00"
}"""
VOTE_NEGATIVE_REQUEST = """{
"mac":"MAC",
"tagId": "TAG_ID",
"isPositive": false,
"timestamp": "2014-09-18T10:32:59+00:00"
}"""
SELL_DATA_REQUEST = """{
"mac":"MAC",
"tagId": "TAG_ID"
}"""


class NfcEndpointTest(FlaskrWithMongoTest, unittest.TestCase):
    def test_should_get_list_of_all_users(self):
        self.db.users.insert(user_in_db())
        self.db.users.insert(user_in_db(confirmed=True))

        response = self.app.get('/contacts')

        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(json.loads(response.data), [{"name": "Jan Kowalski", "email": "jan@kowalski.com"}])

    def test_returns_404_if_user_not_found(self):
        response = self.app.put('/contact/%s/%s' % (USER_EMAIL_ADDRESS, NFC_TAG_ID))

        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.status_code, 404)

    def test_should_assign_new_tag_to_user(self):
        self.db.users.insert(user_in_db(confirmed=True))

        response = self.app.put('/contact/%s/%s' % (USER_EMAIL_ADDRESS, NFC_TAG_ID))

        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.status_code, 201)
        self.assertIn(NFC_TAG_ID, self.db.users.find_one()['nfcTags'])

    def test_returns_200_if_tag_already_associated_with_given_user(self):
        self.db.users.insert(user_in_db(confirmed=True))

        self.app.put('/contact/%s/%s' % (USER_EMAIL_ADDRESS, NFC_TAG_ID))
        response = self.app.put('/contact/%s/%s' % (USER_EMAIL_ADDRESS, NFC_TAG_ID))

        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.status_code, 200)

    def test_overrides_if_tag_already_associated_with_another_user(self):
        self.db.users.insert(user_in_db(confirmed=True, email="bob@example.com"))
        first_response = self.app.put('/contact/%s/%s' % ("bob@example.com", NFC_TAG_ID))
        self.assertEqual(first_response.status_code, 201)

        self.db.users.insert(user_in_db(confirmed=True))
        second_response = self.app.put('/contact/%s/%s' % (USER_EMAIL_ADDRESS, NFC_TAG_ID))

        self.assertEqual(second_response.content_type, "application/json")
        self.assertEqual(second_response.status_code, 201)
        self.assertEqual(find_user_for_tag(NFC_TAG_ID)['email'], USER_EMAIL_ADDRESS)
        self.assertEqual(self.db.users.find_one({"email": "bob@example.com"})['deletedNfcTags'], [NFC_TAG_ID])


    def test_should_find_user_for_given_tag(self):
        self.db.users.insert(user_in_db(confirmed=True, nfcTags=[NFC_TAG_ID]))

        response = self.app.get('/contact/%s' % NFC_TAG_ID)

        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.status_code, 200)

    def test_should_limit_finding_user_by_tag(self):
        self.db.users.insert(user_in_db(confirmed=True, nfcTags=[NFC_TAG_ID]))
        for i in range(50):
            response = self.app.get('/contact/%s?requester=x' % NFC_TAG_ID)
            self.assertEqual(response.status_code, 200)

        response = self.app.get('/contact/%s?requester=x' % NFC_TAG_ID)
        self.assertEqual(response.status_code, 429)

    def test_returns_404_if_user_not_found_by_tag(self):
        response = self.app.get('/contact/%s' % NFC_TAG_ID)

        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.status_code, 404)

    def test_should_register_new_votes(self):
        raise SkipTest()
        response = self.app.post('/vote', data=VOTE_POSITIVE_REQUEST, content_type="application/json")

        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.status_code, 201)

    def test_should_register_changed_votes(self):
        raise SkipTest()
        first_response = self.app.post('/vote', data=VOTE_POSITIVE_REQUEST, content_type="application/json")
        self.assertEqual(first_response.status_code, 201)

        second_response = self.app.post('/vote', data=VOTE_NEGATIVE_REQUEST, content_type="application/json")

        self.assertEqual(second_response.content_type, "application/json")
        self.assertEqual(second_response.status_code, 200)

    def test_should_register_not_changed_votes(self):
        raise SkipTest()
        first_response = self.app.post('/vote', data=VOTE_POSITIVE_REQUEST, content_type="application/json")
        self.assertEqual(first_response.status_code, 201)

        second_response = self.app.post('/vote', data=VOTE_POSITIVE_REQUEST, content_type="application/json")

        self.assertEqual(second_response.content_type, "application/json")
        self.assertEqual(second_response.status_code, 304)

    def test_should_register_data_sellouts(self):
        response = self.app.post('/selldata', data=SELL_DATA_REQUEST, content_type="application/json")

        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.db.selldata.find_one()['tagId'], NFC_TAG_ID)



if __name__ == '__main__':
    unittest.main()
