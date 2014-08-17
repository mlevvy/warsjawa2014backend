# -*- coding: utf-8 -*-
from flask import Flask
from pymongo import MongoClient
from flask import request, g, jsonify
import os, binascii
import mailgunresource
import logging

app = Flask(__name__)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
app.logger.addHandler(handler)


def get_db():
    if not hasattr(g, 'db'):
        g.db = MongoClient('db', 27017).warsjawa
    return g.db


@app.route('/users', methods=['POST'])
def add_new_user():
    request_json = request.json
    request_json['key'] = binascii.hexlify(os.urandom(128)).decode('UTF-8')
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


@app.route('/emails/<workshop_id>', methods=['POST'])
def register_new_email_for_workshop(workshop_id):
    workshop = get_db().workshops.find_and_modify(
        query={"workshopId": workshop_id},
        update={"$addToSet": {"emails": request.json}}
    )
    if workshop is None:
        return """{"message": "Workshop %s not found"}""" % workshop_id, 404
    else:
        return "", 201


@app.route('/emails/<workshop_id>/<attender_email>', methods=['PUT'])
def register_new_user_for_workshop(workshop_id, attender_email):
    workshop = get_db().workshops.find_and_modify(
        query={"workshopId": workshop_id},
        update={"$push": {"users": attender_email}}
    )
    if workshop is None:
        return """{"message": "Workshop %s not found"}""" % workshop_id, 404

    user = get_db().users.find_one({"email": attender_email})
    if user is None:
        return """{"message": "User %s not found"}""" % attender_email, 412

    sent_emails_id = []

    for mail in workshop['emails']:
        if mail['emailId'] not in user['emails']:
            mailgunresource.send_workshop_mail(attender_email, mail['subject'], mail['text'])
            sent_emails_id.append(mail['emailId'])

    get_db().users.update(
        {"_id": user['_id']},
        {"$push": {"emails": {"$each": sent_emails_id}}}
    )
    return "", 200


@app.route('/emails/<workshop_id>/<attender_email>', methods=['DELETE'])
def unregister_user_from_workshop(workshop_id, attender_email):
    update_result = get_db().workshops.update({"workshopId": workshop_id}, {"$pull": {"users": attender_email}})
    if update_result['updatedExisting']:
        return "", 200
    else:
        return "", 404

@app.route("/emails/<workshop_id>", methods=['GET'])
def get_workshop_emails(workshop_id):
    # Well, I could use aggregation, but it is not implemented in mongomock :(
    data = get_db().emails.find_one({"workshopId": workshop_id}, {"emails.emailId": 0})

    if data is None:
        return "", 404

    trimmed_emails = data['emails']
    for email in trimmed_emails:
        email.pop("emailId", None)

    json_data = jsonify(emails=trimmed_emails)
    return json_data


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=80)
    app.run()