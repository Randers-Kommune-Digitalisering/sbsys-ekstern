import base64
import json
import uuid
import datetime

from flask import Flask, Response, jsonify, request
from healthcheck import HealthCheck
from sbsys_operations import SBSYSOperations
from openid_integration import AuthorizationHelper
from config import DEBUG, KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_AUDIENCE
from request_validation import is_cpr, is_pdf, is_timestamp


app = Flask(__name__)
health = HealthCheck()
ah = AuthorizationHelper(KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_AUDIENCE)
sbsys = SBSYSOperations()


app.add_url_rule("/healthz", "healthcheck", view_func=lambda: health.run())

# In-memory collection of SignaturFileupload objects
signatur_fileuploads = {}


class SignaturFileupload:
    def __init__(self, file, timestamp: str, cpr: str):
        self.file = file
        self.timestamp = timestamp
        self.cpr = cpr
        self.id = str(uuid.uuid4())  # Generate a unique ID as a string

    def __repr__(self):
        return f"<file:{self.file} timestamp:{self.timestamp} cpr:{self.cpr} id:{self.id}>"

    def fetch_id(self):
        return self.id


@app.route('/api/journaliser/ansattelse/fil', methods=['POST'])
@ah.authorization
def sbsys_journaliser_ansattelse_fil():
    try:
        # Get form data
        cpr = request.form.get('cpr', None)
        timestamp = request.form.get('timestamp', None)
        file = request.files.get('file', None)
        id = request.form.get('id', None)

        upload = None
        if not (cpr and timestamp and file) and not id:
            return jsonify({"error": "Missing form-data parameter, must contain cpr, timestamp and file, or id"}), 400

        if file and timestamp and cpr:
            if not is_cpr(cpr):
                return jsonify(
                    {"error": "Not a valid cpr number. It must be digits in either 'ddmmyyxxxx' or 'ddmmyy-xxxx' format"}), 400

            if not is_timestamp(timestamp):
                return jsonify({"error": "Timestamp is not in ISO 8601 format."}), 400

            if not is_pdf(file):
                return jsonify({"error": "Not a valid PDF file"}), 400

            # Create and store the SignaturFileupload object
            upload = SignaturFileupload(file=file, timestamp=timestamp, cpr=cpr)
            signatur_fileuploads[upload.fetch_id()] = upload

        if id:
            # Fetch Fileupload object with id
            upload = signatur_fileuploads.get(id)

            if not upload:
                return jsonify({"error": "No upload object was found with given id. Please retry with cpr, timestamp and file, to generate an upload object"}), 404

            cpr = upload.cpr
            timestamp = upload.timestamp
            file = upload.file

        if not upload:
            return jsonify({"error": "No upload object found or created. Please retry with cpr, timestamp and file, to generate an upload object"}), 404

        # Find newest personalesag based on CPR from request
        sag = fetch_sag(cpr)

        # Check if sag is None
        if sag is None:
            return jsonify(
                {**success_message(False, upload), "reason": "Failed to find active case based on given cpr"}), 200

        # Convert timestamp to datetime
        timestamp_datetime = datetime.datetime.fromisoformat(timestamp)
        case_creation_time = datetime.datetime.strptime(sag["Oprettet"], "%Y-%m-%dT%H:%M:%S.%f%z")
        time_difference_seconds = (case_creation_time - timestamp_datetime).total_seconds()

        # Check if the time difference is within 5 minutes (300 seconds)
        if time_difference_seconds <= 300:
            print("The case is within 5 minutes before or any time after the timestamp.")
            journalise_document(sag, file, upload)

            # Remove the upload object from the list after successful journalising
            del signatur_fileuploads[upload.fetch_id()]

            return jsonify({**success_message(True, upload), "cpr": upload.cpr, "timestamp": timestamp}), 200
        else:
            print("The case is not within 5 minutes before or any time after the timestamp.")
            print("Found case creation time: " + sag['Oprettet'] + "\n timestamp: " + str(upload.timestamp))
            return jsonify(
                {**success_message(False, upload), "reason": "Case is not created after timestamp minus 5 minutes"}), 200

    except JournalisationError as e:
        return jsonify({"error": e.message}), e.status_code

    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500


def success_message(success: bool, upload: SignaturFileupload):
    if success:
        return {"success": success, "message": "File was uploaded successfully", "id": upload.id, "cpr": upload.cpr, "timestamp": upload.timestamp}
    else:
        return {"success": success, "message": "File upload can be attempted using id", "id": upload.id, "cpr": upload.cpr, "timestamp": upload.timestamp}


def fetch_sag(cpr):
    # Find newest personalesag based on CPR from request
    return sbsys.find_newest_personalesag({"cpr": cpr, "sagType": {"Id": 5}})


class JournalisationError(Exception):
    def __init__(self, reason, status_code, upload):
        self.reason = reason
        self.status_code = status_code
        self.message = success_message(False, upload)


def journalise_document(sag: object, file, upload):
    # For a given sag, save the array of delforloeb
    delforloeb_array = sbsys.find_personalesag_delforloeb(sag)
    if len(delforloeb_array) < 1:
        raise JournalisationError("Failed to find delforløb, try again", 500, upload)

    delforloeb_object_from_index = delforloeb_array[0]  # Select the first delforloeb object
    delforloeb_id = delforloeb_object_from_index["ID"]  # Save the unique ID of the delforloeb object

    # Journalise file
    response = sbsys.journalise_file(sag, file, delforloeb_id)

    # Check if sag is None
    if response is None:
        raise JournalisationError("Failed to journalise file, try again", 500, upload)


if __name__ == "__main__":
    app.run(debug=DEBUG, host='0.0.0.0', port=8080)
