# -*- coding: utf-8 -*-
import re
import os
import binascii
import logging
import datetime
from functools import wraps

from flask import Flask
from pymongo import MongoClient
from flask import request, g, jsonify

import mailgunresource


app = Flask(__name__)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
app.logger.addHandler(handler)
app.logger.setLevel(logging.DEBUG)


def simple_response(message, success):
    return jsonify({"success": success, "message": message})


def error_response(message):
    return simple_response(message, True)


def success_response(message):
    return simple_response(message, False)


def get_db():
    if not hasattr(g, 'db'):
        g.db = MongoClient('db', 27017).warsjawa
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

    if get_db().users.find({"email": request_json['email']}).count() == 0:
        return error_response("User not found"), 404

    find_result = get_db().users.update(
        {"email": request_json['email'], "key": request_json['key'], "isConfirmed": False},
        {"$set": {"isConfirmed": True}})

    if find_result['n'] > 0:
        mailgunresource.send_confirm_user(request_json)
        return success_response("User is confirmed now."), 201
    else:
        mailgunresource.send_deny_confirm_user(request_json)
        return error_response("Invalid key."), 304


@app.route('/emails/<workshop_id>', methods=['POST'])
@with_logging()
def register_new_email_for_workshop(workshop_id):
    request_json = request.json
    request_json['emailId'] = generate_email_id()
    request_json['date'] = datetime.datetime.now()

    workshop = get_db().workshops.find_and_modify(
        query={"workshopId": workshop_id},
        update={"$addToSet": {"emails": request.json}}
    )
    if workshop is None:
        return error_response("Workshop %s not found." % workshop_id), 404
    else:
        return success_response("User registered."), 201


@app.route('/emails/<workshop_id>/<attender_email>', methods=['PUT'])
@with_logging()
def register_new_user_for_workshop(workshop_id, attender_email):
    workshop = get_db().workshops.find_and_modify(
        query={"workshopId": workshop_id},
        update={"$addToSet": {"users": attender_email}}
    )
    if workshop is None:
        return error_response("Workshop %s not found" % workshop_id), 404

    user = get_db().users.find_one({"email": attender_email})
    if user is None:
        return error_response("User %s not found" % attender_email), 412
    elif user['isConfirmed'] is not True:
        return error_response("User %s not confirmed" % attender_email), 412

    sent_emails_id = []

    for mail in workshop['emails']:
        if mail['emailId'] not in user['emails']:
            mailgunresource.send_workshop_mail(attender_email, mail['subject'], mail['text'])
            sent_emails_id.append(mail['emailId'])

    get_db().users.update(
        {"_id": user['_id']},
        {"$push": {"emails": {"$each": sent_emails_id}}}
    )
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

    trimmed_emails = data['emails']
    for email in trimmed_emails:
        email.pop("emailId", None)

    json_data = jsonify(emails=trimmed_emails)
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
    email_id = generate_email_id()
    email = {
        'emailId': email_id,
        'raw': request.form,
        'files': request.files,
        'subject': request.form['subject'],
        'text': request.form['body-plain']
    }
    workshop_secret = get_workshop_secret_from_email_address(email_address)
    workshop = get_db().workshops.find_and_modify(
        query={"emailSecret": workshop_secret},
        update={"$push": {"emails": email}}
    )
    if workshop is None:
        return error_response("Workshop not found"), 404  # TODO send reply that invalid email was sent?

    for user_email in workshop['users']:
        to_send_data = dict()
        to_send_data['from'] = request.form['from']
        to_send_data['to'] = user_email
        to_send_data['subject'] = request.form['subject']
        to_send_data['text'] = request.form['body-plain']
        if 'body-html' in request.form:
            to_send_data['html'] = request.form['body-html']

        mailgunresource.send_mail_raw(
            data=to_send_data,
            files=request.files.to_dict()
        )
        get_db().users.update(
            {"email": user_email},
            {"$push": {"emails": email_id}}
        )
    return success_response("Email processed.")


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=80)
    app.run()
