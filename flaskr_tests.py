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


if __name__ == '__main__':
    unittest.main()
