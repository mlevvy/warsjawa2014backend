# -*- coding: utf-8 -*-
from flask import Flask
from pymongo import MongoClient
from flask import request
from flask import g
import os, binascii
import mailgunresource

app = Flask(__name__)

# TODO Dodaj walidację requestów


def get_db():
    if not hasattr(g, 'db'):
        g.db = MongoClient('db', 27017)
    return g.db


@app.route('/users', methods=['POST'])
def add_new_user():
    request_json = request.json
    request_json['key'] = binascii.b2a_hex(os.urandom(128))
    request_json['isConfirmed'] = False

    find_result = get_db().users.find_one({"email": request_json['email']})
    if find_result is None or find_result['isConfirmed'] is False:
        get_db().users.update({"email": request_json['email']}, {"$set": request_json}, upsert=True)
        mailgunresource.send_add_new_user(request_json)
        return "", 201
    else:
        mailgunresource.send_deny_new_user(request_json)
        return "", 304


@app.route('/users', methods=['PUT'])
def confirm_new_user():
    request_json = request.json

    if get_db().users.find({"email": request_json['email']}).count() == 0:
        return """{"message": "User not found"}""", 404

    find_result = get_db().users.update(
        {"email": request_json['email'], "key": request_json['key'], "isConfirmed": False},
        {"$set": {"isConfirmed": True}})

    if find_result['n'] > 0:
        mailgunresource.send_confirm_user(request_json)
        return "", 201
    else:
        mailgunresource.send_deny_confirm_user(request_json)
        return "", 304


if __name__ == '__main__':
    app.run()