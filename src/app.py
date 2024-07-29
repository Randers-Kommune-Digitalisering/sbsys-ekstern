from flask import Flask, request
from healthcheck import HealthCheck

import http_status as status
from sbsys_operations import SBSYSOperations
from openid_integration import AuthorizationHelper
from config import DEBUG, KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_AUDIENCE
from request_validation import is_cpr, is_employment, is_pdf, is_timestamp
from utils import generate_response, STATUS_CODE, SignaturFileupload

app = Flask(__name__)
health = HealthCheck()
ah = AuthorizationHelper(KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_AUDIENCE)
sbsys = SBSYSOperations()


app.add_url_rule("/healthz", "healthcheck", view_func=lambda: health.run())


# In-memory collection of SignaturFileupload objects
signatur_fileuploads = {}


@app.route('/api/journaliser/ansattelse/fil', methods=['POST', 'PUT'])
@ah.authorization
def sbsys_journaliser_ansattelse_fil():
    try:

        # Get form data
        id = request.form.get('id', None)
        cpr = request.form.get('cpr', None)
        employment = request.form.get('employment', None)
        file = request.files.get('file', None)
        
        upload = None
        http_status_code = status.HTTP_201_CREATED
        msg = "File created"

        if request.method == 'POST':
            if not (cpr and employment and file):
                return generate_response("Missing form-data parameter, must contain cpr, employment and file", http_code=status.HTTP_400_BAD_REQUEST)
            else:
                if not is_cpr(cpr):
                    return generate_response("Not a valid cpr number. It must be digits in either 'ddmmyyxxxx' or 'ddmmyy-xxxx' format", status.HTTP_400_BAD_REQUEST)

                if not is_employment(employment):
                    return generate_response("Employment is not a five digit integer.", status.HTTP_400_BAD_REQUEST)

                if not is_pdf(file):
                    return generate_response("Not a valid PDF file", status.HTTP_400_BAD_REQUEST)
                
                upload = SignaturFileupload(file=file, employment=employment, cpr=cpr)
                signatur_fileuploads[upload.get_id()] = upload

        elif request.method == 'PUT':
            if id:
                upload = signatur_fileuploads.get(id)
                if upload:
                    if cpr:
                        if is_cpr(cpr):
                            upload.cpr = cpr
                        else:
                            return generate_response("Not a valid cpr number. It must be digits in either 'ddmmyyxxxx' or 'ddmmyy-xxxx' format", status.HTTP_400_BAD_REQUEST)
                    if employment:
                        if is_employment(employment):
                            upload.employment = employment
                        else:
                            return generate_response("Employment is not a five digit integer.", status.HTTP_400_BAD_REQUEST)
                    if file:
                        if is_pdf(file):    
                            upload.file = file
                        else:    
                            return generate_response("Not a valid PDF file", status.HTTP_400_BAD_REQUEST)

                    upload.status = STATUS_CODE.RECEIVED
                    http_status_code = status.HTTP_200_OK
                    msg = "File updated"
                else:
                    return generate_response("File not found", status.HTTP_404_NOT_FOUND, received_id=id)
            else:
                return generate_response("Missing id parameter", status.HTTP_400_BAD_REQUEST)

        else:
            raise Exception("Unsupported HTTP method")

        return generate_response(msg, http_status_code, upload)

    except Exception as e:
        print(f"Unexpected error: {e}")
        return generate_response("An unexpected error occurred", status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.route('/api/journaliser/ansattelse/fil', methods=['GET'])
@ah.authorization
def sbsys_journaliser_ansattelse_fil_status():
    id = request.args.get('id', None)
    if id:
        upload = signatur_fileuploads.get(id)
        if upload:
            # TODO: Fix message
            return generate_response(status.HTTP_202_ACCEPTED, upload)
        return generate_response("File not found", status.HTTP_404_NOT_FOUND, received_id=id)
    else:
        return generate_response("Missing id parameter", status.HTTP_400_BAD_REQUEST)


@app.teardown_request
def mocking(exception):
    for job in signatur_fileuploads.values():
        # remove files
        job.file = None

        # mock work
        if job.employment == "00001":
            job.status = STATUS_CODE.SUCCESS
            job.message = "File was uploaded successfully"
        elif job.employment == "00002":
            job.status = STATUS_CODE.PROCESSING
            job.message = "Looking for case in SBSYS"
        elif job.employment == "00003":
            pass # keep as received or updated
        elif job.employment == "00004":
            job.status = STATUS_CODE.FAILED_TRY_AGAIN
            job.message = "Failed to upload file, try again"
        elif job.employment == "00005":
            job.status = STATUS_CODE.FAILED
            job.message = "Failed to connect to SBSYS"


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
