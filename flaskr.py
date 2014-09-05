# -*- coding: utf-8 -*-
import re
import os
import binascii
import logging
from functools import wraps

from flask import Flask
from pymongo import MongoClient
from flask import request, g, jsonify
import yaml

from emails import MailMessageCreator, EmailMessage, generate_email_id
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
    return simple_response(message, False)


def success_response(message):
    return simple_response(message, True)


def get_db():
    if not hasattr(g, 'db'):
        g.db = MongoClient('db', 27017).warsjawa
    return g.db


def load_workshops():
    def generate_workshop_email_secret():
        return binascii.hexlify(os.urandom(8)).decode('UTF-8')

    def create_workshop(yaml_data):
        new_workshop = {
            'workshopId': yaml_data['workshopId'],
            'emailSecret': generate_workshop_email_secret(),
            'name': yaml_data['name'],
            'mentors': yaml_data['mentors'],
            'users': [],
            'emails': []
        }
        return new_workshop

    yaml_file = open("workshops.yml", encoding="utf-8")
    workshops = yaml.load(yaml_file)['workshops']
    app.logger.info("There are %d workshops" % len(workshops))
    for workshop_data in workshops:
        workshop_in_db = get_db().workshops.find_one({"workshopId": workshop_data['workshopId']})
        if workshop_in_db is not None:
            app.logger.debug("Skipping %s" % workshop_data)
            continue  # skip already inserted
        else:
            workshop_in_db = create_workshop(workshop_data)
            get_db().workshops.insert(workshop_in_db)
            welcome_message = MailMessageCreator.mentor_welcome_email(workshop_in_db['name'],
                                                                      workshop_in_db['emailSecret'])
            for email in workshop_in_db['mentors']:
                welcome_message.send(to=email)
            app.logger.info("Added %s" % workshop_data)


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
    if not isinstance(json, dict):
        return False
    if set(json.keys()) != {"email", "name"}:
        return False
    return True


@app.route('/users', methods=['POST'])
@with_logging()
def add_new_user():
    request_json = request.get_json(force=True, silent=True)
    if not is_valid_new_user_request(request_json):
        return error_response("Invalid request. Should contain only 'email' and 'name'."), 400
    request_json['key'] = binascii.hexlify(os.urandom(128)).decode('UTF-8')
    request_json['isConfirmed'] = False
    request_json['emails'] = []

    find_result = get_db().users.find_one({"email": request_json['email']})
    if find_result is None or find_result['isConfirmed'] is False:
        get_db().users.update({"email": request_json['email']}, {"$set": request_json}, upsert=True)
        message = MailMessageCreator.user_registration(request_json['name'], request_json['key'])
        message.send(to=request_json['email'])
        return success_response("Registration email sent."), 201
    else:
        mailgunresource.send_deny_new_user(request_json)
        return error_response("User already registered."), 304


def is_valid_confirm_user_request(json):
    if not isinstance(json, dict):
        return False
    if set(json.keys()) != {"email", "key"}:
        return False
    return True


@app.route('/users', methods=['PUT'])
@with_logging()
def confirm_new_user():
    request_json = request.get_json(force=True, silent=True)
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
        message = MailMessageCreator.user_confirmation(user['name'], user['key'])
        message.send(to=request_json['email'])
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
    workshop['emails'] = [EmailMessage.from_db_dict(e) for e in workshop['emails']]
    ensure_mails_were_sent_to_users(workshop['emails'], [attender_email], workshop)
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

    emails = [EmailMessage.from_db_dict(email).as_response() for email in data['emails']]
    json_data = jsonify(emails=emails)
    return json_data


def get_workshop_secret_from_email_address(email_address):
    regex = re.compile("(.*-)?workshop-(.*)@system.warsjawa.pl", re.IGNORECASE)
    match = regex.match(email_address)
    if match is None:
        raise AttributeError("%s does not match expected format" % email_address)
    return match.group(2)


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
        update={"$push": {"emails": email.as_db_dict()}}
    )
    if workshop is None:
        return error_response("Workshop not found"), 404  # TODO send reply that invalid email was sent?

    ensure_mails_were_sent_to_users([email], workshop['users'], workshop)
    return success_response("Email processed.")


def ensure_email_is_sent_to_user(email_message, user_email, workshop):
    update_result = get_db().users.update(
        {"email": user_email,
         "emails": {"$ne": email_message.email_id}},
        {"$addToSet": {"emails": email_message.email_id}}
    )
    if update_result['n'] == 0:  # no documents updated so user not exists or already seen this mail
        return
    else:
        message_to_send = MailMessageCreator.forward_workshop_message(email_message, workshop)
        message_to_send.send(to=user_email)


def ensure_mails_were_sent_to_users(email_messages, users_emails, workshop):
    for email_message in email_messages:
        for user_email in users_emails:
            ensure_email_is_sent_to_user(email_message, user_email, workshop)


if __name__ == '__main__':
    with app.app_context():
        load_workshops()
    app.run(host="0.0.0.0", port=80)
