from flask import Flask, request
from healthcheck import HealthCheck

import http_status as status
from sbsys_operations import SBSYSOperations
from openid_integration import AuthorizationHelper
from database import DatabaseClient, Base, SignaturFileupload, FileObject
from config import DEBUG, KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_AUDIENCE, DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER
from request_validation import is_cpr, is_employment, is_institution, is_pdf, is_timestamp
from utils import generate_response, STATUS_CODE#, SignaturFileupload

app = Flask(__name__)
health = HealthCheck()
ah = AuthorizationHelper(KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_AUDIENCE)
sbsys = SBSYSOperations()
db_client = DatabaseClient('postgresql', DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT)

app.add_url_rule("/healthz", "healthcheck", view_func=lambda: health.run())

# Set up the database
Base.metadata.create_all(db_client.get_engine())


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
            with db_client.get_session() as session:
                if id:
                    # Fetch Fileupload object with id
                    upload = db_client.get_signatur_file_upload(session, id)
                    # upload = signatur_fileuploads.get(id)

                    if not upload:
                        return generate_response("File not found", status.HTTP_404_NOT_FOUND, received_id=id)

                    if not any([cpr, employment, institutionIdentifier, file]) and upload:
                        upload.set_status(STATUS_CODE.RECEIVED, "File upload updated")
                        session.commit()
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
                    session.commit()
                    return generate_response('', status.HTTP_200_OK, upload)
                else:
                    upload = SignaturFileupload(file=file, institutionIdentifier=institutionIdentifier, employment=employment, cpr=cpr)
                    if  db_client.add_object(session, upload):
                        return generate_response('', status.HTTP_201_CREATED, upload)
                    else:
                        raise Exception("Unexpected error occurred")
                    
                    #signatur_fileuploads[upload.get_id()] = upload
                    #return generate_response('', status.HTTP_201_CREATED, upload)

    except Exception as e:
        print(f"Unexpected error: {e}")
        return generate_response("An unexpected error occurred", status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.route('/api/journaliser/ansattelse/fil', methods=['GET'])
@ah.authorization
def sbsys_journaliser_ansattelse_fil_status():
    try:
        id = request.args.get('id', None)
        if id:
            with db_client.get_session() as session:
                upload = db_client.get_signatur_file_upload(session, id)
                # upload = signatur_fileuploads.get(id)
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
    with db_client.get_session() as session:
        for job in db_client.get_all_signatur_file_uploads(session):
            # mock work
            if job.employment == "00000":
                # Don't touch the job if it has failed, succeeded or is processing - thread safety and reupload issues!
                if job.status == STATUS_CODE.RECEIVED:
                    job.set_status(STATUS_CODE.PROCESSING, "Looking for case in SBSYS")
                    cpr = job.cpr
                    if cpr not in ["0211223989", "021122-3989"]:
                        job.set_status(STATUS_CODE.FAILED, "No cases for person")
                    else:
                        try:
                            sag = fetch_sag(cpr)  # Just get the newest
                            if sag:
                                if journalise_document(sag, job):
                                    job.set_status(STATUS_CODE.SUCCESS, "File was uploaded successfully")
                            else:
                                job.set_status(STATUS_CODE.FAILED_TRY_AGAIN, "No case found in SBSYS, try again")
                        except Exception as e:
                            print(f"Unexpected error: {e}")
                            job.set_status(STATUS_CODE.FAILED, "An unexpected error occurred")
            if job.employment == "00001":
                job.set_status(STATUS_CODE.SUCCESS, "File was uploaded successfully")
            elif job.employment == "00002":
                job.set_status(STATUS_CODE.PROCESSING, "Looking for case in SBSYS")
            elif job.employment == "00003":
                pass  # Keep state (RECEIVED)
            elif job.employment == "00004":
                job.set_status(STATUS_CODE.FAILED_TRY_AGAIN, "Failed to upload file, try again")
            elif job.employment == "00005":
                job.set_status(STATUS_CODE.FAILED, "Failed to connect to SBSYS")
        session.commit()


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

@app.route('/test', methods=['GET'])
def test():
    db_client.execute_sql("""
         CREATE TABLE IF NOT EXISTS cars (
         brand VARCHAR(255),
         model VARCHAR(255),
         year INT
    );""")
    db_client.execute_sql("INSERT INTO cars (brand, model, year) VALUES ('bil', 'cool', 2000)")
    res = db_client.execute_sql('SELECT * FROM cars')
    return str(res.fetchall()), 200


if __name__ == "__main__":
    app.run(debug=DEBUG, host='0.0.0.0', port=8080)
