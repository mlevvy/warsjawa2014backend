# -*- coding: utf-8 -*-
import re
import os
import binascii
import logging
from functools import wraps

from flask import Flask
from pymongo import MongoClient
from flask import request, g, jsonify
from pymongo.son_manipulator import SONManipulator

import mailgunresource


app = Flask(__name__)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
app.logger.addHandler(handler)
app.logger.setLevel(logging.DEBUG)


class EmailMessage():
    def __init__(self, email_id, sender, subject, text, html=None, date=None, files=None, raw_message=None):
        self.email_id = email_id
        self.sender = sender
        self.subject = subject
        self.text = text
        self.html = html
        self.date = date
        self.files = files
        self.raw_message = raw_message

    def as_request_to_send(self, recipient):
        return {
            'to': recipient,
            'from': self.sender,
            'subject': self.subject,
            'text': self.text,
            'html': self.html
        }

    def as_db_dict(self):
        return {
            'from': self.sender,
            'subject': self.subject,
            'text': self.text,
            'html': self.html,
            'date': self.date,
            'files': self.files,
            'raw_message': self.raw_message,
            '_type': "EmailMessage"
        }

    def as_response(self):
        return {
            'from': self.sender,
            'subject': self.subject,
            'text': self.text,
            'date': self.date
        }

    @classmethod
    def from_db_dict(cls, value):
        return EmailMessage(**value)


class Transform(SONManipulator):
    def transform_incoming(self, son, collection):
        for (key, value) in son.items():
            if isinstance(value, EmailMessage):
                son[key] = value.as_db_dict()
            elif isinstance(value, dict):
                son[key] = self.transform_incoming(value, collection)
        return son

    def transform_outgoing(self, son, collection):
        for (key, value) in son.items():
            if isinstance(value, dict):
                if "_type" in value and value["_type"] == "EmailMessage":
                    son[key] = EmailMessage.from_db_dict(value)
                else:
                    son[key] = self.transform_outgoing(value, collection)
        return son


def simple_response(message, success):
    return jsonify({"success": success, "message": message})


def error_response(message):
    return simple_response(message, False)


def success_response(message):
    return simple_response(message, True)


def get_db():
    if not hasattr(g, 'db'):
        g.db = MongoClient('db', 27017).warsjawa
        g.db.add_son_manipulator(Transform())
    return g.db


def with_logging():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            app.logger.debug("%s: %s", request, request.get_data(as_text=True, parse_form_data=True))
            rv = f(*args, **kwargs)
            app.logger.debug("Response: %s", rv)
            return rv

        return decorated_function

    return decorator


def is_valid_new_user_request(json):
    if set(json.keys()) != {"email", "name"}:
        return False
    return True


@app.route('/users', methods=['POST'])
@with_logging()
def add_new_user():
    request_json = request.json
    if not is_valid_new_user_request(request_json):
        return error_response("Invalid request. Should contain only 'email' and 'name'."), 400
    request_json['key'] = binascii.hexlify(os.urandom(128)).decode('UTF-8')
    request_json['isConfirmed'] = False
    request_json['emails'] = []

    find_result = get_db().users.find_one({"email": request_json['email']})
    if find_result is None or find_result['isConfirmed'] is False:
        get_db().users.update({"email": request_json['email']}, {"$set": request_json}, upsert=True)
        mailgunresource.send_add_new_user(request_json)
        return success_response("Registration email sent."), 201
    else:
        mailgunresource.send_deny_new_user(request_json)
        return error_response("User already registered."), 304


def is_valid_confirm_user_request(json):
    if set(json.keys()) != {"email", "key"}:
        return False
    return True


@app.route('/users', methods=['PUT'])
@with_logging()
def confirm_new_user():
    request_json = request.json
    if not is_valid_confirm_user_request(request_json):
        return error_response("Invalid request. Should contain only 'email' and 'key'."), 400

    user = get_db().users.find_one({"email": request_json['email']})
    if user is None:
        return error_response("User not found"), 404

    if user['isConfirmed']:
        mailgunresource.send_deny_confirm_user(request_json)
        return error_response("User already confirmed."), 304

    find_result = get_db().users.update(
        {"email": request_json['email'], "key": request_json['key']},
        {"$set": {"isConfirmed": True}})

    if find_result['n'] > 0:
        mailgunresource.send_confirm_user(request_json)
        return success_response("User is confirmed now."), 200
    else:
        mailgunresource.send_deny_confirm_user(request_json)
        return error_response("Invalid key."), 403


@app.route('/emails/<workshop_id>/<attender_email>', methods=['PUT'])
@with_logging()
def register_new_user_for_workshop(workshop_id, attender_email):
    user = get_db().users.find_one({"email": attender_email})
    if user is None:
        return error_response("User %s not found" % attender_email), 412
    elif user['isConfirmed'] is not True:
        return error_response("User %s not confirmed" % attender_email), 412

    workshop = get_db().workshops.find_and_modify(
        query={"workshopId": workshop_id},
        update={"$addToSet": {"users": attender_email}}
    )
    if workshop is None:
        return error_response("Workshop %s not found" % workshop_id), 404
    if attender_email in workshop['users']:
        return error_response("User %s is already registered for %s" % (attender_email, workshop_id)), 304

    ensure_mails_were_sent_to_users(workshop['emails'], [attender_email])
    return success_response("User %s registered for %s" % (attender_email, workshop_id)), 200


@app.route('/emails/<workshop_id>/<attender_email>', methods=['DELETE'])
@with_logging()
def unregister_user_from_workshop(workshop_id, attender_email):
    update_result = get_db().workshops.update({"workshopId": workshop_id}, {"$pull": {"users": attender_email}})
    if update_result['updatedExisting']:
        return success_response("Registration of user %s for %s is cancelled" % (attender_email, workshop_id)), 200
    else:
        return error_response("Workshop %s not found" % workshop_id), 404


@app.route("/emails/<workshop_id>", methods=['GET'])
@with_logging()
def get_workshop_emails(workshop_id):
    # Well, I could use aggregation, but it is not implemented in mongomock :(
    data = get_db().workshops.find_one({"workshopId": workshop_id}, {"emails.emailId": 0})

    if data is None:
        return error_response("Workshop %s not found" % workshop_id), 404

    emails = [email.as_response() for email in data['emails']]
    json_data = jsonify(emails=emails)
    return json_data


def get_workshop_secret_from_email_address(email_address):
    regex = re.compile("(.*-)?workshop-(.*)@system.warsjawa.pl", re.IGNORECASE)
    match = regex.match(email_address)
    if match is None:
        raise AttributeError("%s does not match expected format" % email_address)
    return match.group(2)


def generate_email_id():
    return binascii.hexlify(os.urandom(32)).decode('UTF-8')


@app.route("/mailgun", methods=['POST'])
@with_logging()
def accept_incoming_emails():
    email_address = request.form['recipient']
    email = EmailMessage(
        email_id=generate_email_id(),
        sender=request.form['from'],
        subject=request.form['subject'],
        text=request.form['body-plain'],
        html=request.form['body-html']
    )
    workshop_secret = get_workshop_secret_from_email_address(email_address)
    workshop = get_db().workshops.find_and_modify(
        query={"emailSecret": workshop_secret},
        update={"$push": {"emails": email}}
    )
    if workshop is None:
        return error_response("Workshop not found"), 404  # TODO send reply that invalid email was sent?

    ensure_mails_were_sent_to_users([email], workshop['users'])
    return success_response("Email processed.")


def ensure_email_is_sent_to_user(email_message, user_email):
    update_result = get_db().users.update(
        {"email": user_email,
         "emails": {"$not": email_message.email_id}},
        {"$addToSet": {"emails": email_message.email_id}}
    )
    if update_result['n'] == 0:  # no documents updated so user not exists or already seen this mail
        return
    else:
        request_data = email_message.as_request_to_send(recipient=user_email)
        mailgunresource.send_mail_raw(
            data=request_data
        )


def ensure_mails_were_sent_to_users(email_messages, users_emails):
    for email_message in email_messages:
        for user_email in users_emails:
            ensure_email_is_sent_to_user(email_message, user_email)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=80)
    app.run()
