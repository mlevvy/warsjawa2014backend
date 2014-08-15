# -*- coding: utf-8 -*-
import unittest

import mongomock

import flaskr


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
