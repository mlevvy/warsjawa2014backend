# -*- coding: utf-8 -*-
from flask import Flask
from pymongo import MongoClient
from flask import request
from flask import g
import os, binascii

app = Flask(__name__)

# TODO Dodaj walidację requestów

def get_db():
    if not hasattr(g, 'db'):
        g.db = MongoClient('db', 27017)
    return g.db


@app.route('/users', methods=['POST'])
def get_all_emails():
    rjson = request.json
    rjson['key'] = binascii.b2a_hex(os.urandom(128))
    rjson['isConfirmed'] = False
    get_db().users.update({"email": rjson['email']}, {"$set": rjson}, upsert=True)
    return "", 201


if __name__ == '__main__':
    app.run()