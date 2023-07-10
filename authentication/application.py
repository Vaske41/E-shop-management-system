from flask import Flask, request, Response, jsonify
from configuration import Configuration
from models import database, User, UserRole
from email_validator import validate_email, EmailNotValidError
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt, get_jwt_identity
from sqlalchemy import and_
import json

def isValid(email):
    try:
        email = validate_email(email)
        return True
    except EmailNotValidError as e:
        return False

application = Flask(__name__)
application.config.from_object(Configuration)

@application.route("/register_customer", methods=["POST"])
def register_customer():
    email = request.json.get("email", "")
    password = request.json.get("password", "")
    forename = request.json.get("forename", "")
    surname = request.json.get("surname", "")

    emailEmpty = email == None or len(email) == 0
    passwordEmpty = password == None or len(password) == 0
    forenameEmpty = forename == None or len(forename) == 0
    surnameEmpty = surname == None or len(surname) == 0


    if forenameEmpty:
        return Response(json.dumps({'message': 'Field forename is missing.'}), status=400)
    if surnameEmpty:
        return Response(json.dumps({'message': 'Field surname is missing.'}), status=400)
    if emailEmpty:
        return Response(json.dumps({'message': 'Field email is missing.'}), status=400)
    if passwordEmpty:
        return Response(json.dumps({'message': 'Field password is missing.'}), status=400)

    validEmail = isValid(email)
    if not validEmail:
        return Response(json.dumps({'message': 'Invalid email.'}), status=400)
    if len(password) < 8:
        return Response(json.dumps({'message': 'Invalid password.'}), status=400)

    user = User.query.filter(User.email == email).first()
    if user:
        return Response(json.dumps({'message': 'Email already exists.'}), status=400)

    user = User(email=email, password=password, forename=forename, surname=surname)
    database.session.add(user)
    database.session.commit()

    userRole = UserRole(userId=user.id, roleId=1)
    database.session.add(userRole)
    database.session.commit()

    return Response(status=200)

@application.route("/register_courier", methods=["POST"])
def register_courier():
    email = request.json.get("email", "")
    password = request.json.get("password", "")
    forename = request.json.get("forename", "")
    surname = request.json.get("surname", "")

    emailEmpty = email == None or len(email) == 0
    passwordEmpty = password == None or len(password) == 0
    forenameEmpty = forename == None or len(forename) == 0
    surnameEmpty = surname == None or len(surname) == 0


    if forenameEmpty:
        return Response(json.dumps({'message': 'Field forename is missing.'}), status=400)
    if surnameEmpty:
        return Response(json.dumps({'message': 'Field surname is missing.'}), status=400)
    if emailEmpty:
        return Response(json.dumps({'message': 'Field email is missing.'}), status=400)
    if passwordEmpty:
        return Response(json.dumps({'message': 'Field password is missing.'}), status=400)

    validEmail = isValid(email)
    if not validEmail:
        return Response(json.dumps({'message': 'Invalid email.'}), status=400)
    if len(password) < 8:
        return Response(json.dumps({'message': 'Invalid password.'}), status=400)

    user = User.query.filter(User.email == email).first()
    if user:
        return Response(json.dumps({'message': 'Email already exists.'}), status=400)

    user = User(email=email, password=password, forename=forename, surname=surname)
    database.session.add(user)
    database.session.commit()

    userRole = UserRole(userId=user.id, roleId=3)
    database.session.add(userRole)
    database.session.commit()

    return Response(status=200)


jwt = JWTManager(application)


@application.route("/login", methods=["POST"])
def login():
    email = request.json.get("email", "")
    password = request.json.get("password", "")

    emailEmpty = email == None or len(email) == 0
    passwordEmpty = password == None or len(password) == 0

    if emailEmpty:
        return Response(json.dumps({'message': 'Field email is missing.'}), status=400)
    elif passwordEmpty:
        return Response(json.dumps({'message': 'Field password is missing.'}), status=400)
    validEmail = isValid(email)
    if not validEmail:
        return Response(json.dumps({'message': 'Invalid email.'}), status=400)

    user = User.query.filter(and_(User.email == email, User.password == password)).first()

    if not user:
        return Response(json.dumps({'message': 'Invalid credentials.'}), status=400)

    additionalClaims = {
        "forename": user.forename,
        "surname": user.surname,
        "roles": [str(role) for role in user.roles]
    }

    accessToken = create_access_token(identity=user.email, additional_claims=additionalClaims)

    return jsonify(accessToken=accessToken)


@application.route("/check", methods=["POST"])
@jwt_required()
def check():
    return "Token is valid!"

@application.route("/delete", methods=["POST"])
@jwt_required()
def refresh():
    identity = get_jwt_identity()

    user = User.query.filter(User.email == identity).first()
    if not user:
        return Response(json.dumps({'message': 'Unknown user.'}), status=400)

    database.session.delete(user)
    database.session.commit()

    return Response(status=200)


@application.route("/", methods=["GET"])
def index():
    return "Hello world!"


if __name__ == "__main__":
    database.init_app(application)
    application.run(debug=True, host="0.0.0.0", port=5000)
