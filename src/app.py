from flask import Flask, request
from healthcheck import HealthCheck
from datetime import datetime

import sys
import atexit
import signal
import logging
import threading
import http_status as status
from sbsys_operations import SBSYSOperations
from openid_integration import AuthorizationHelper
from database import DatabaseClient, Base, SignaturFileupload  # , FileObject
from config import DEBUG, KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_AUDIENCE, DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER, SD_URL, SD_USERNAME, SD_PASSWORD
from request_validation import is_cpr, is_employment, is_institution, is_pdf  # , is_timestamp
from utils import set_logging_configuration, generate_response, STATUS_CODE  # , SignaturFileupload
from sd.sd_client import SDClient
from browserless import browserless_sd_personalesag_files

set_logging_configuration()

health = HealthCheck()
ah = AuthorizationHelper(KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_AUDIENCE)
sbsys = SBSYSOperations()
sd_client = SDClient(username=SD_USERNAME, password=SD_PASSWORD, url=SD_URL)
db_client = DatabaseClient('postgresql', DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT)
logger = logging.getLogger(__name__)


# Set up the database
Base.metadata.create_all(db_client.get_engine())


def create_app():

    app = Flask(__name__)
    app.add_url_rule("/healthz", "healthcheck", view_func=lambda: health.run())
    return app


app = create_app()


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

                    if not upload:
                        return generate_response("File not found", status.HTTP_404_NOT_FOUND, received_id=id)
                    
                    if upload.status == STATUS_CODE.SUCCESS:
                        return generate_response("File has already been uploaded", status.HTTP_400_BAD_REQUEST, received_id=id)
                    
                    if upload.status == STATUS_CODE.PROCESSING:
                        return generate_response("File is being processed", status.HTTP_400_BAD_REQUEST, received_id=id)

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
                    if db_client.add_object(session, upload):
                        return generate_response('', status.HTTP_201_CREATED, upload)
                    else:
                        raise Exception("Unexpected error occurred")

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


# @app.teardown_request
# def mocking(exception):
#     with db_client.get_session() as session:
#         for job in db_client.get_all_signatur_file_uploads(session):
#             # mock work
#             if job.employment == "00000":
#                 # Don't touch the job if it has failed, succeeded or is processing - thread safety and reupload issues!
#                 if job.status == STATUS_CODE.RECEIVED:
#                     job.set_status(STATUS_CODE.PROCESSING, "Looking for case in SBSYS")
#                     cpr = job.cpr
#                     if cpr not in ["0211223989", "021122-3989"]:
#                         job.set_status(STATUS_CODE.FAILED, "No cases for person")
#                     else:
#                         try:
#                             sag = fetch_sag(cpr)  # Just get the newest
#                             if sag:
#                                 if journalise_document(sag, job):
#                                     job.set_status(STATUS_CODE.SUCCESS, "File was uploaded successfully")
#                             else:
#                                 job.set_status(STATUS_CODE.FAILED_TRY_AGAIN, "No case found in SBSYS, try again")
#                         except Exception as e:
#                             print(f"Unexpected error: {e}")
#                             job.set_status(STATUS_CODE.FAILED, "An unexpected error occurred")
#             if job.employment == "00001":
#                 job.set_status(STATUS_CODE.SUCCESS, "File was uploaded successfully")
#             elif job.employment == "00002":
#                 job.set_status(STATUS_CODE.PROCESSING, "Looking for case in SBSYS")
#             elif job.employment == "00003":
#                 pass  # Keep state (RECEIVED)
#             elif job.employment == "00004":
#                 job.set_status(STATUS_CODE.FAILED_TRY_AGAIN, "Failed to upload file, try again")
#             elif job.employment == "00005":
#                 job.set_status(STATUS_CODE.FAILED, "Failed to connect to SBSYS")
#         session.commit()


def success_message(success: bool, upload: SignaturFileupload):
    if success:
        return {"success": success, "message": "File was uploaded successfully", "id": upload.id, "cpr": upload.cpr, "timestamp": upload.timestamp}
    else:
        return {"success": success, "message": "File upload can be attempted using id", "id": upload.id, "cpr": upload.cpr, "timestamp": upload.timestamp}


def fetch_sag(cpr):
    # Find newest personalesag based on CPR from request
    return sbsys.find_newest_personalesag({"cpr": cpr, "sagType": {"Id": 5}})


def fetch_personalesag(cpr, employment_identifier, institution_identifier):

    return find_personalesag_by_sd_employment(
        cpr=cpr,
        employment_identifier=employment_identifier,
        inst_code=institution_identifier,
    )

def find_personalesag_by_sd_employment(cpr: str, employment_identifier: str, inst_code: str):
    # Fetch SD employment
    employment = sd_client.GetEmployment20111201(cpr=cpr, employment_identifier=employment_identifier, inst_code=inst_code)
    if not employment:
        logger.warning(f"No employment found with cpr: {cpr}, employment_identifier: {employment_identifier}, or inst_code: {inst_code}")
        return None

    employment_location_code = employment.get('EmploymentDepartment', None).get('DepartmentIdentifier', None)
    if not employment_location_code:
        logger.warning(f"No department identifier found with cpr: {cpr}, employment_identifier: {employment_identifier}, and inst_code: {inst_code}")
        return None

    institutions_and_departments = sd_client.fetch_departments(inst_identifier=inst_code)

    if not institutions_and_departments:
        logger.warning(f"No institutions_and_departments were found on region code 9R")
        return None

    # Fetch the person active personalesager
    sager = sbsys.fetch_active_personalesager(cpr)

    if not sager:
        logger.warning(f"No sag found with cpr: {cpr}")
        return

    # Go through sager and compare ansaettelsessted from sag to DepartmentCode from SD employment
    for sag in sager:
        matched_sag = compare_sag_ansaettelssted(sag, employment, institutions_and_departments)
        if matched_sag:
            return matched_sag

    input_strings = [f'{cpr} {employment_identifier}']
    sd_employment_files = fetch_sd_employment_files(input_strings)

    if not sd_employment_files:
        logger.warning("sd_employment_files is None")
        return None

    sd_file_result = sd_employment_files.get('allResults', None)
    if not sd_file_result:
        logger.warning("sd_file_result is None")
        return None

    if not len(sd_file_result) == 1:
        logger.warning(f"sd_file_result has a length of '{len(sd_file_result)}', but it should have a length of '1'")
        return None

    # Select the first element of the list with one element
    sd_file_result = sd_file_result[0]
    # Check if result is empty
    if not sd_file_result['result']:
        # Go through sager and compare ansaettelsessted from sag to DepartmentCode from SD employment
        for sag in sager:
            matched_sag = compare_sag_ansaettelssted(sag, employment, institutions_and_departments)
            if matched_sag:
                return matched_sag

    # Go through sager and compare file name and archive date with personalesag in SD
    for sag in sager:
        sag_id = sag.get('Id', None)

        if not sag_id:
            logger.info(f"sag_id is None - No sag id found for sag with cpr: {cpr}")
            continue

        # Fetch the files from given delforloeb in current sag
        matched_sag = compare_sag_and_results(sd_file_result, sag)
        if not matched_sag:
            continue

        # logger.debug(matched_sag)
        return matched_sag

    return None


def compare_sag_ansaettelssted(sag: dict, employment, institutions_and_departments):
    sag_id = sag.get('Id', None)

    if not sag_id:
        logger.warning(f"sag_id is None - No sag id found in compare_sag_ansaettelssted")
        return None

    sag_employment_location = sag.get('Ansaettelsessted', None).get('Navn', None)
    if not sag_employment_location:
        logger.info(f"sag_employment_location is None - No Ansaettelsessted found on sag id: {sag_id}")
        return None

    department_codes = find_department_codes(institutions_and_departments, sag_employment_location)
    if not department_codes:
        logger.info(
            f"department_codes is None - sag with id: {sag_id} {sag_employment_location} does not correspond with any SD departments")
        return None

    # Compare the sag_employment_location from personalesag to departmentname
    employment_location_match_list = filter_employment_by_department([employment],
                                                                     department_codes['DepartmentCodes'], sag_id,
                                                                     sag_employment_location)
    if len(employment_location_match_list) == 1 and employment_location_match_list[0]['MatchData']:
        logger.info(f"Match found for ansaettelsessted between employment_identifier, and sag_id: "
                    f"{employment_location_match_list[0].get('EmploymentIdentifier', None)}"
                    f", {sag_id}")
        return sag
    elif len(employment_location_match_list) > 1:
        logger.warning(
            f"employment_location_match_list has a length of: {len(employment_location_match_list)} - It should have a legth of one, since there is only one employment")
    else:
        return None
        logger.debug(
            f"No personalesag match found for employment_identifier, and employment_department: {employment.get('EmploymentIdentifier', None)},"
            f" {employment.get('EmploymentDepartment', None).get('DepartmentIdentifier', None)}"
            f" \nFound sag with id, and location: {sag_id}, {sag_employment_location} - Which has department code {department_codes['DepartmentCodes']}")
    return None


def compare_sag_and_results(sd_result: dict, sag: dict):
    sag_id = sag.get('Id', None)
    if not sag_id:
        logger.warning("compare_sag_and_results received None sag_id")
        return None

    if not sd_result:
        logger.warning("compare_sag_and_results received None sd_result")
        return None

    # Fetch the files from given delforloeb in current sag
    sag_documents = sbsys.fetch_delforloeb_files(sag_id=sag_id, delforloeb_title="01 Ansættelse",
                                              allowed_filetypes=[], document_keywords=[])

    if not sag_documents:
        logger.info(f"sag with id: {sag_id} has no documents")
        return None

    logger.info(f"Comparing for inputString: {sd_result['inputString']}")

    all_match = True  # Assume all documents will match initially

    for document in sag_documents:
        try:
            # Convert RegistreringsDato to the same format as arkivdato for comparison
            registrerings_dato = datetime.strptime(document['RegistreringsDato'], "%Y-%m-%dT%H:%M:%S.%f%z").strftime(
                "%d.%m.%Y")
        except ValueError:
            # Handle cases where there might be no microseconds
            registrerings_dato = datetime.strptime(document['RegistreringsDato'], "%Y-%m-%dT%H:%M:%S%z").strftime("%d.%m.%Y")

        # Remove excess whitespace in document Navn
        sag_navn = ' '.join(document['Navn'].split())

        # Check if there's any item in sd_result that matches both navn and arkivdato
        match_found = False
        for item in sd_result['result']:
            if item['navn'] == sag_navn and item['arkivdato'] == registrerings_dato:
                # logger.info(f"Match found: {item} for sag: {sag_id}")
                match_found = True
                break

        if not match_found:
            # logger.info(f"No match found for document {document} in sag: {sag_id}")
            all_match = False
            break  # If any document doesn't match, we can stop the comparison

    return sag if all_match else None


def find_department_codes(inst_list: list, sag_employment_location: str):
    def recursive_search(department):
        if isinstance(department, list):
            codes = []
            for dept in department:
                result = recursive_search(dept)
                if result:
                    codes.extend(result['DepartmentCodes'])
            return {
                'DepartmentCodeName': sag_employment_location,
                'DepartmentCodes': list(set(codes))  # Ensure unique codes
            } if codes else None
        elif isinstance(department, dict):
            codes = []
            department_name = department.get('DepartmentName', '')
            # Ensure department_name is a string and not None
            if isinstance(department_name, str):
                # Check for partial match with full string
                if sag_employment_location in department_name:
                    codes.append(department.get('DepartmentIdentifier'))
                # Check if DepartmentCodeName is exactly 30 characters
                if len(department_name) == 30 and sag_employment_location.startswith(department_name):
                    codes.append(department.get('DepartmentIdentifier'))
            # Recursively search within nested departments
            if 'Department' in department and department['Department'] is not None:
                result = recursive_search(department['Department'])
                if result:
                    codes.extend(result['DepartmentCodes'])
            return {
                'DepartmentCodeName': sag_employment_location,
                'DepartmentCodes': list(set(codes))  # Ensure unique codes
            } if codes else None
        return None

    all_codes = []
    for institution in inst_list:
        result = recursive_search(institution.get('Department', {}))
        if result:
            all_codes.append(result)

    # Combine results for the same department name
    combined_results = {}
    for item in all_codes:
        if item['DepartmentCodeName'] in combined_results:
            combined_results[item['DepartmentCodeName']]['DepartmentCodes'].extend(item['DepartmentCodes'])
            combined_results[item['DepartmentCodeName']]['DepartmentCodes'] = list(
                set(combined_results[item['DepartmentCodeName']]['DepartmentCodes']))
        else:
            combined_results[item['DepartmentCodeName']] = item

    # Convert combined results to a list
    result_list = list(combined_results.values())

    # Return a single object if there is exactly one match, otherwise return the list
    if len(result_list) == 1:
        return result_list[0]
    return result_list


def filter_employment_by_department(employment_list, department_code_list, sag_id, department_name):
    filtered_employment = []
    for department_code in department_code_list:
        for employment in employment_list:
            if employment.get('EmploymentDepartment', {}).get('DepartmentIdentifier') == department_code:
                employment['MatchData'] = {
                    'SagId': sag_id,
                    'DepartmentName': department_name,
                    'DepartmentCode': department_code
                }
                filtered_employment.append(employment)
    return filtered_employment


def fetch_sd_employment_files(input_strings: list):
    try:
        # Make the request and get the response
        response = browserless_sd_personalesag_files(input_strings)

        # Check if the response status code is 200
        if response.status_code == 200:
            # Return the content if the status is 200
            return response.json()  # Assuming the content is JSON
        else:
            # Handle the error case (you can raise an exception or return an error message)
            raise Exception(f"Request failed with status code: {response.status_code}")
    except Exception as e:
        logger.error(f"fetch_sd_employment_files error: {e}")
        return None


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


worker_stop_event = threading.Event()


def worker_job():
    logger = logging.getLogger('worker_thread')
    logger.info("Worker started")
    while not worker_stop_event.is_set():
        with db_client.get_session() as sess:
            upload_file = db_client.get_next_signatur_file_upload(sess)
            if upload_file:
                sag = fetch_personalesag(upload_file.cpr, upload_file.employment, upload_file.institutionIdentifier)
                if sag:
                    if journalise_document(sag, upload_file):
                        upload_file.set_status(STATUS_CODE.SUCCESS, "File was uploaded successfully")
                else:
                    upload_file.set_status(STATUS_CODE.FAILED, "No case found in SBSYS")
            sess.commit()
    logger.info("Worker stopped")


worker = threading.Thread(target=worker_job)


def stop_worker():
    global worker, worker_stop_event
    worker_stop_event.set()
    worker.join()


def shutdown_server(sig, frame):
    stop_worker()
    sys.exit(0)


if __name__ == "__main__":
    worker.start()
    atexit.register(stop_worker)
    signal.signal(signal.SIGINT, shutdown_server)
    app.run(debug=DEBUG, host='0.0.0.0', port=8080)
