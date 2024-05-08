import base64
import json

from flask import Flask, Response, jsonify, request
from healthcheck import HealthCheck
from sbsys_operations import SBSYSOperations
from openid_integration import AuthorizationHelper
from config import DEBUG, KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_AUDIENCE
from request_validation import is_cpr, is_pdf
import datetime


app = Flask(__name__)
health = HealthCheck()
ah = AuthorizationHelper(KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_AUDIENCE)
sbsys = SBSYSOperations()


app.add_url_rule("/healthz", "healthcheck", view_func=lambda: health.run())


@app.route('/api/journaliser/ansattelse/fil', methods=['POST'])
@ah.authorization
def sbsys_journaliser_ansattelse_fil():
    # Get form data
    cpr = request.form.get('cpr', None)
    file = request.files.get('file', None)

    if not cpr or not file:
        return jsonify({"error": "Missing parameter, must contain cpr and file"}), 400

    if not is_cpr(cpr):
        return jsonify({"error": "Not a valid cpr number. It must be digits in either 'xxxxxxxxxx' or 'xxxxxx-xxxx' format"}), 400

    if not is_pdf(file):
        return jsonify({"error": "Not a valid PDF file"}), 400

    # Find newest personalesag based on CPR from request
    sag = sbsys.find_newest_personalesag({"cpr":cpr, "sagType": {"Id": 5}})

    # Check if sag is None
    if sag is None:
        return jsonify({"error": "Failed to find active case based on given cpr"}), 400

    # Check if the case is older than 24 hours
    now = datetime.datetime.now(datetime.timezone.utc)
    case_creation_time = datetime.datetime.strptime(sag["Oprettet"], "%Y-%m-%dT%H:%M:%S.%f%z")
    time_difference = now - case_creation_time
    if time_difference.days > 0:  # 24 hours
        return jsonify({"error": "Failed to find case based on given cpr. The case is older than 24 hours."}), 400

    # For a given sag, save the array of delforloeb
    delforloeb_array = sbsys.find_personalesag_delforloeb(sag)
    if len(delforloeb_array) < 1:
        return jsonify({"error": "Failed to find delforløb, try again"}), 500

    delforloeb_object_from_index = delforloeb_array[0]  # Select the first delforloeb object
    delforloeb_id = delforloeb_object_from_index["ID"]  # Save the unique ID of the delforloeb object

    # Journalise file
    response = sbsys.journalise_file(sag, file, delforloeb_id)

    # Check if sag is None
    if response is None:
        return jsonify({"error": "Failed to journalise file, try again"}), 500

    # TODO Hvordan skal filen journaliseres? delforløb, navn, type.
    return jsonify({"success": "File uploaded successfully"}), 200

if __name__ == "__main__":
    app.run(debug=DEBUG, host='0.0.0.0', port=8080)
