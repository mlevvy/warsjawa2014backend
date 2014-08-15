import unittest

from flaskr_tests import FlaskrWithMongoTest


class EmailsEndpointTest(FlaskrWithMongoTest, unittest.TestCase):
    def test_should_save_user_registration_in_database_when_user_selects_workshop(self):
        pass  # TODO test

    def test_should_send_emails_for_workshop_when_user_selects_workshop(self):
        pass  # TODO test

    def test_should_not_send_emails_already_sent_to_this_user(self):
        pass  # TODO test




if __name__ == '__main__':
    unittest.main()
