import base64
import json

from flask import Flask, Response, jsonify, request
from healthcheck import HealthCheck

from request_validation import validate_request_journaliser_fil
from sbsys_operations import SBSYSOperations
from openid_integration import AuthorizationHelper

from config import DEBUG, KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_CLIENT_ID, KEYCLOAK_CLIENT_SECRET, ADD_FILE_ROLE


app = Flask(__name__)
health = HealthCheck()
ah = AuthorizationHelper(KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_CLIENT_ID, KEYCLOAK_CLIENT_SECRET)

app.add_url_rule("/healthz", "healthcheck", view_func=lambda: health.run())


@app.route('/api/token', methods=["POST"])
def token():
    if request.is_json and type(request.json) == dict:
        username = request.json.get('username', None)
        password = request.json.get('password', None)
        status, res = ah.get_token(username, password)
    else:
        status = 400
        res = json.dumps({"error": "invalid_content", "error_description": "Payload is not json"})
    return Response(res, status=status, mimetype='application/json')


@app.route('/api/refreshtoken', methods=["POST"])
def refesh_token():
    if request.is_json and type(request.json) == dict:
        token = request.json.get('refreshtoken', None)
        status, res = ah.refresh_token(token)
    else:
        status = 400
        res = json.dumps({"error": "invalid_content", "error_description": "Payload is not json"})
    return Response(res, status=status, mimetype='application/json')


@app.route('/api/logout', methods=["POST"])
def logout():
    if request.is_json and type(request.json) == dict:
        token = request.json.get('refreshtoken', None)
        status, res = ah.logout(token)
    else:
        status = 400
        res = json.dumps({"error": "invalid_content", "error_description": "Payload is not json"})
    return Response(res, status=status, mimetype='application/json')


@app.route('/api/journaliser/fil', methods=['POST'])
@ah.authorization(ADD_FILE_ROLE)
def sbsys_journaliser_fil():

    # Check if request contains JSON data
    if not request.is_json:
        return jsonify({"error": "Request must contain JSON data"}), 400

    # Extract JSON data from request
    data = request.json

    # Validate the request
    validation_result, error_response = validate_request_journaliser_fil(data)
    if not validation_result:
        return jsonify(error_response), 400  # Return error response if validation fails

    # Find newest personalesag based on CPR from request
    cpr = request.json.get('cpr')
    sbsys = SBSYSOperations()
    sag = sbsys.find_newest_personalesag(cpr)
    
    # Check if sag is None
    if sag is None:
        return jsonify({"error": "Failed to retrieve search results based on given cpr"}), 500

    # Journalise file 
    fil = request.json.get('fil')
    binary_data = base64.b64decode(fil)

    response = sbsys.journalise_file(sag, binary_data)
    # Check if sag is None
    if response is None:
        return jsonify({"error": "Failed to journalise file, try again"}), 500

    print(response)

    # TODO journaliser fil fra request på sagen fra find_newest_personalesag
    # TODO Hvordan skal filen journaliseres? delforløb, navn, type.
    return jsonify({"success": "Fil uploaded successfully"}), 200


if __name__ == "__main__":
    app.run(debug=DEBUG, host='0.0.0.0', port=8080)
