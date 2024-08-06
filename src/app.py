from flask import Flask, request
from healthcheck import HealthCheck

import http_status as status
from sbsys_operations import SBSYSOperations
from openid_integration import AuthorizationHelper
from config import DEBUG, KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_AUDIENCE
from request_validation import is_cpr, is_employment, is_institution, is_pdf, is_timestamp
from utils import generate_response, STATUS_CODE, SignaturFileupload

app = Flask(__name__)
health = HealthCheck()
ah = AuthorizationHelper(KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_AUDIENCE)
sbsys = SBSYSOperations()


app.add_url_rule("/healthz", "healthcheck", view_func=lambda: health.run())


# In-memory collection of SignaturFileupload objects
signatur_fileuploads = {}

# TODO: Handling of files is not threadsafe, consider using a database or a queue!

@app.route('/api/journaliser/ansattelse/fil', methods=['POST', 'PUT'])
@ah.authorization
def sbsys_journaliser_ansattelse_fil():
    try:
        # Get form data
        id = request.form.get('id', None)
        cpr = request.form.get('cpr', None)
        employment = request.form.get('employment', None)
        institutionIdentifier = request.form.get('institutionIdentifier', None)
        file = request.files.get('file', None)

        upload = None

        if not id and not all([cpr,employment, file, institutionIdentifier]):
            return generate_response("Missing form-data parameter, must contain cpr, institution, employment and file", http_code=status.HTTP_400_BAD_REQUEST)
        else:
            if id:
                # Fetch Fileupload object with id
                upload = signatur_fileuploads.get(id)

                if not upload:
                    return generate_response("File not found", status.HTTP_404_NOT_FOUND, received_id=id)

                if not any([cpr, employment, institutionIdentifier, file]) and upload:
                    upload.set_status(STATUS_CODE.RECEIVED, "File upload updated")
                    return generate_response('', status.HTTP_200_OK, upload)
                elif not all([cpr, employment, institutionIdentifier, file]) and upload:
                    return generate_response("Missing form-data parameter, must contain cpr, institution, employment and file", http_code=status.HTTP_400_BAD_REQUEST, received_id=id)
            
            if not is_cpr(cpr):
                return generate_response("Not a valid cpr number. It must be digits in either 'ddmmyyxxxx' or 'ddmmyy-xxxx' format", status.HTTP_400_BAD_REQUEST)

            if not is_employment(employment):
                return generate_response("Employment is not a five digit integer.", status.HTTP_400_BAD_REQUEST)
            
            if not is_institution(institutionIdentifier):
                return generate_response("Not a valid PDF file", status.HTTP_400_BAD_REQUEST)

            if not is_pdf(file):
                return generate_response("Not a valid PDF file", status.HTTP_400_BAD_REQUEST)
            
            if upload:
                upload.update_values(file=file, institutionIdentifier=institutionIdentifier, employment=employment, cpr=cpr)
                return generate_response('', status.HTTP_200_OK, upload)
            else:
                upload = SignaturFileupload(file=file, institutionIdentifier=institutionIdentifier, employment=employment, cpr=cpr)
                signatur_fileuploads[upload.get_id()] = upload

                return generate_response('', status.HTTP_201_CREATED, upload)

    except Exception as e:
        print(f"Unexpected error: {e}")
        return generate_response("An unexpected error occurred", status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.route('/api/journaliser/ansattelse/fil', methods=['GET'])
@ah.authorization
def sbsys_journaliser_ansattelse_fil_status():
    try:
        id = request.args.get('id', None)
        if id:
            upload = signatur_fileuploads.get(id)
            if upload:
                # TODO: Fix message
                msg, status_code = generate_response('', http_code=status.HTTP_200_OK, upload=upload)
                return msg, status_code
            else:
                return generate_response("File not found", status.HTTP_404_NOT_FOUND, received_id=id)
        else:
            return generate_response("Missing id parameter", status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        print(f"Unexpected error: {e}")
        return generate_response("An unexpected error occurred", status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.teardown_request
def mocking(exception):
    for job in signatur_fileuploads.values():

        # mock work
        if job.employment == "00000":
            # Don't touch the job if it has failed, succeeded or is processing - thread safety and reupload issues!
            if job.status == STATUS_CODE.RECEIVED:
                job.set_status(STATUS_CODE.PROCESSING, "Looking for case in SBSYS")
                cpr = job.cpr
                if cpr not in ["0211223989", "021122-3989"]:
                    job.set_status(STATUS_CODE.FAILED, "No cases for person")
                    job.file = None
                else:
                    try:
                        sag = fetch_sag(cpr)  # Just get the newest
                        if sag:
                            if journalise_document(sag, job):
                                job.set_status(STATUS_CODE.SUCCESS, "File was uploaded successfully")
                        else:
                            job.set_status(STATUS_CODE.FAILED_TRY_AGAIN, "No case found in SBSYS, try again")
                            job.file = None
                    except Exception as e:
                        print(f"Unexpected error: {e}")
                        job.set_status(STATUS_CODE.FAILED, "An unexpected error occurred")
        if job.employment == "00001":
            job.set_status(STATUS_CODE.SUCCESS, "File was uploaded successfully")
            job.file = None
        elif job.employment == "00002":
            job.set_status(STATUS_CODE.PROCESSING, "Looking for case in SBSYS")
            job.file = None
        elif job.employment == "00003":
            pass  # Keep state (RECEIVED)
        elif job.employment == "00004":
            job.set_status(STATUS_CODE.FAILED_TRY_AGAIN, "Failed to upload file, try again")
            job.file = None
        elif job.employment == "00005":
            job.set_status(STATUS_CODE.FAILED, "Failed to connect to SBSYS")
            job.file = None


def success_message(success: bool, upload: SignaturFileupload):
    if success:
        return {"success": success, "message": "File was uploaded successfully", "id": upload.id, "cpr": upload.cpr, "timestamp": upload.timestamp}
    else:
        return {"success": success, "message": "File upload can be attempted using id", "id": upload.id, "cpr": upload.cpr, "timestamp": upload.timestamp}


def fetch_sag(cpr):
    # Find newest personalesag based on CPR from request
    return sbsys.find_newest_personalesag({"cpr": cpr, "sagType": {"Id": 5}})


class JournalisationError(Exception):
    pass


def journalise_document(sag: object, upload):
    # For a given sag, save the array of delforloeb
    delforloeb_array = sbsys.find_personalesag_delforloeb(sag)
    if len(delforloeb_array) < 1:
        upload.set_status(STATUS_CODE.FAILED, "No delforloeb found for case")
        return None

    delforloeb_object_from_index = delforloeb_array[0]  # Select the first delforloeb object
    delforloeb_id = delforloeb_object_from_index["ID"]  # Save the unique ID of the delforloeb object

    # Journalise file
    response = sbsys.journalise_file(sag, upload.file, delforloeb_id, upload.id)

    # Check if sag is None
    if response is None:
        upload.set_status(STATUS_CODE.FAILED_TRY_AGAIN, "Failed to upload file, try again")

    return response


if __name__ == "__main__":
    app.run(debug=DEBUG, host='0.0.0.0', port=8080)