from flask import Flask, request
from healthcheck import HealthCheck
from datetime import datetime

import sys
import atexit
import signal
import time
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
from browserless import browserless_sd_personalesag_files, browserless_sd_personalesag_exist

set_logging_configuration()

health = HealthCheck()
ah = AuthorizationHelper(KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_AUDIENCE)
sbsys = SBSYSOperations()
sd_client = SDClient(username=SD_USERNAME, password=SD_PASSWORD, url=SD_URL)
db_client = DatabaseClient('postgresql', DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT)
logger = logging.getLogger(__name__)


# Set up the database
# Base.metadata.create_all(db_client.get_engine())


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


def fetch_personalesag(cpr, employment_identifier, institution_identifier, level_3_departments):

    return find_personalesag_by_sd_employment(
        cpr=cpr,
        employment_identifier=employment_identifier,
        inst_code=institution_identifier,
        level_3_departments=level_3_departments
    )


def find_personalesag_by_sd_employment(cpr: str, employment_identifier: str, inst_code: str, level_3_departments: dict):
    # Fetch SD employment
    employment = sd_client.GetEmployment20111201(cpr=cpr, employment_identifier=employment_identifier, inst_code=inst_code)
    if not employment:
        logger.warning(f"No employment found with cpr: {cpr}, employment_identifier: {employment_identifier}, and inst_code: {inst_code}")
        return None

    employment_location_code = employment.get('EmploymentDepartment', None).get('DepartmentIdentifier', None)
    if not employment_location_code:
        logger.warning(f"No department identifier found with cpr: {cpr}, employment_identifier: {employment_identifier}, and inst_code: {inst_code}")
        return None

    institutions_and_departments = sd_client.fetch_departments(inst_identifier=inst_code)

    if not institutions_and_departments:
        logger.warning("No institutions_and_departments were found on region code 9R")
        return None

    # Fetch the person active personalesager
    sager = sbsys.fetch_active_personalesager(cpr)

    input_string = '{cpr} {employment_identifier}'

    if not sager:
        logger.info(f"No sag found with cpr: {cpr} - trying to force create personalesag")
        res_dict = check_sd_has_personalesag(input_string)
        if res_dict.get('success', None):
            logger.info(f"Personalesag was created for cpr: {cpr} - trying to fetch sager again")
            sager = sbsys.fetch_active_personalesager(cpr)

    if not sager:
        logger.error(f"No sag found with cpr: {cpr}")
        return None

    # Go through sager and compare ansaettelsessted from sag to DepartmentCode from SD employment
    for sag in sager:
        matched_sag = compare_sag_ansaettelssted(sag, employment, institutions_and_departments)
        if matched_sag:
            return matched_sag

    # No matched sag - trying to create personalesag
    res_dict = check_sd_has_personalesag(input_string)
    if res_dict.get('success', None):
        logger.info(f"Personalesag was created for cpr: {cpr} - trying to fetch sager again")
        sager = sbsys.fetch_active_personalesager(cpr)

    # Go through sager and compare ansaettelsessted from sag to DepartmentCode from SD employment
    for sag in sager:
        matched_sag = compare_sag_ansaettelssted(sag, employment, institutions_and_departments)
        if matched_sag:
            return matched_sag
        # Match on level 3 department
        else:
            matched_sag = compare_sd_and_sbsys_employment_place_by_level_3(sag, employment, level_3_departments)
            if matched_sag:
                return matched_sag

    logger.error(f"No sag found matching: {cpr} {employment_identifier}- No match found between SD and SBSYS")

    return None


def compare_sag_ansaettelssted(sag: dict, employment, institutions_and_departments):
    sag_id = sag.get('Id', None)

    if not sag_id:
        logger.error("sag_id is None - No sag id found in compare_sag_ansaettelssted")
        return None

    sag_employment_location = sag.get('Ansaettelsessted', None).get('Navn', None)
    if not sag_employment_location:
        logger.error(f"sag_employment_location is None - No Ansaettelsessted found on sag id: {sag_id}")
        return None

    department_codes = find_department_codes(institutions_and_departments, sag_employment_location)
    if not department_codes:
        logger.error(f"department_codes is None - sag with id: {sag_id} {sag_employment_location} does not correspond with any SD departments")
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
    sag_documents = sbsys.fetch_delforloeb_files(sag_id=sag_id, delforloeb_title="01 Ansættelse", allowed_filetypes=[], document_keywords=[])

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


def check_sd_has_personalesag(input_string: str):
    try:
        # Make the request and get the response
        response = browserless_sd_personalesag_exist(input_string)

        # Check if the response status code is 200
        if response.status_code == 200:
            # Return the content if the status is 200
            return response.json()  # Assuming the content is JSON
        else:
            logger.error(f"Request failed with status code: {response.status_code} and message: {response.content}")
    except Exception as e:
        logger.error(f"fetch_sd_employment_files error: {e}")
        return None


class JournalisationError(Exception):
    pass


def journalise_document(sag: object, upload):
    try:
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
    except Exception as e:
        logger.error(f"journalise_document error: {e}")
        upload.set_status(STATUS_CODE.FAILED, "An unexpected error occurred")


# LEVEL 3 stuff START
def fetch_institution_nested(region_identifier):
    path = 'GetOrganization'

    # Define the SD params
    params = {
        'RegionCode': region_identifier

    }

    organization = sd_client.get_request(path, params)
    if organization:
        organization = organization.get('OrganizationInformation', None)
        organization = organization.get('Region', None)
        institution = organization.get('Institution', [])

        return institution
    else:
        logger.error(f"Error while fetching institution nested with region identifier: {region_identifier}")


def fetch_institutions_flattened(region_identifier):
    inst_and_dep = []
    # Get institutions
    path = 'GetInstitution20080201'
    try:
        params = {
            'RegionIdentifier': region_identifier
        }
        response = sd_client.post_request(path=path, params=params)

        if not response:
            logger.warning("No response from SD client")
            return None

        if not response['GetInstitution20080201']:
            logger.warning("GetInstitution20080201 object not found")
            return None

        if not response['GetInstitution20080201']['Region']:
            logger.warning("Region object not found")
            return None
        region = response['GetInstitution20080201']['Region']

        if not region['Institution']:
            logger.warning("Institution list not found")
            return None
        inst_list = region['Institution']

        # Get departments
        path = 'GetDepartment20080201'
        date_today = datetime.now().strftime('%d.%m.%Y')
        for inst in inst_list:
            institution_identifier = inst.get('InstitutionIdentifier', None)
            institution_name = inst.get('InstitutionName', None)

            if not institution_identifier or not institution_name:
                logger.warning("InstitutionIdentifier or InstitutionName is None")
                continue
            # Define the SD params
            params = {
                'InstitutionIdentifier': institution_identifier,
                'ActivationDate': date_today,
                'DeactivationDate': date_today,
                'DepartmentNameIndicator': 'true'
            }

            response = sd_client.post_request(path=path, params=params)

            if not response:
                logger.warning("No response from SD client")
                return None

            if not response['GetDepartment20080201']:
                logger.warning("GetDepartment20080201 object not found")
                return None

            if not response['GetDepartment20080201']['Department']:
                logger.warning("Department list not found")
                return None
            department_list = response['GetDepartment20080201']['Department']

            inst_and_dep_dict = {'InstitutionIdentifier': institution_identifier,
                                 'InstitutionName': institution_name,
                                 'Department': department_list}
            inst_and_dep.append(inst_and_dep_dict)

        return inst_and_dep

    except Exception as e:
        logger.error(f"Error while fetching inst and departments: {e} \n"
                     f"Region code: {region_identifier}")
        return []


def group_by_level_3(region_identifier):
    departments_by_level_3 = {}

    def handle_departments(item, top=None):

        def handle(item, top=None):

            def checkname(name):
                if not name or "UDGÅET" in name or "IKKE I BRUG" in name:
                    return False
                return True

            level = item.get("DepartmentLevel", None)
            code = item.get("DepartmentCode", None)
            name = item.get("DepartmentCodeName", None)

            if not name:
                name = ''

            if int(level) == 3 and not top:
                top = code
                departments_by_level_3[code] = {'codes': []}
            elif top and int(level) < 3:
                if checkname(name):
                    departments_by_level_3[top]['codes'].append(code)
            else:
                if checkname(name):
                    logger.warning(f"SD level 3 - department has no level 3, code: {code}, name: {name}")

            if int(level) > 0:
                handle_departments(item, top)

        if isinstance(item.get("Department", None), dict):
            handle(item.get("Department", None), top)
        elif isinstance(item.get("Department", None), list):
            for department in item.get("Department", None):
                handle(department, top)
        else:
            logger.error("SD level 3 - department - is not a dict or list")

    institutions_nested = fetch_institution_nested(region_identifier)
    if not institutions_nested:
        logger.error("Unable to fetch institutions nested")
        return None

    for item in institutions_nested:
        handle_departments(item)

    institutions_flattened = fetch_institutions_flattened(region_identifier)
    if not institutions_flattened:
        logger.error("Unable to fetch institutions flattened")
        return None
    
    all_departments = []
    for institution in institutions_flattened:
        if isinstance(institution.get("Department", None), list):
            for department in institution.get("Department", None):
                all_departments.append({'code': department.get("DepartmentIdentifier", None), 'name': department.get("DepartmentName", None)})
        else:
            logger.error(f'SD level 3 - Institution with id: {institution.get("InstitutionIdentifier", None)} - Department value is not a list')

    for key, value in departments_by_level_3.items():
        names = []
        for code in value.get('codes'):
            department_name = next((item['name'] for item in all_departments if item["code"] == code), None)
            if department_name:
                names.append(department_name)
            else:
                logger.error(f"SD level 3 - department - code: {code} - name not found")

        departments_by_level_3[key]['names'] = names

    return departments_by_level_3


def compare_sd_and_sbsys_employment_place_by_level_3(sag, employment, level_3_departments):
    for key in level_3_departments:
        if (sag.get('Ansaettelsessted', None).get('Navn', None) in level_3_departments[key].get('names', []) and
                employment.get('EmploymentDepartment', {}).get('DepartmentIdentifier') in level_3_departments[key].get('codes', [])):
            return sag

# LEVEL 3 stuff END


worker_stop_event = threading.Event()


def worker_job():
    logger = logging.getLogger('worker_thread')
    logger.info("Worker started")

    departments_by_level_3 = None
    departments_by_level_3_updated = datetime.now()

    while not worker_stop_event.is_set():
        if not departments_by_level_3 or (datetime.now() - departments_by_level_3_updated).seconds > 43200:
            departments_by_level_3 = group_by_level_3('9R')
            departments_by_level_3_updated = datetime.now()
        with db_client.get_session() as sess:
            upload_file = db_client.get_next_signatur_file_upload(sess)
            if upload_file:

                if not departments_by_level_3:
                    logger.error("No departments found")
                    upload_file.set_status(STATUS_CODE.FAILED, "No departments found")
                    sess.commit()
                else:
                    logger.info(f"Processing file with id: {upload_file.id}")
                    # times_to_try = 3
                    # time_to_sleep = 5
                    # i = 0

                    # while i < times_to_try:
                    sag = fetch_personalesag(upload_file.cpr, upload_file.employment, upload_file.institutionIdentifier, departments_by_level_3)
                    if sag:
                        if journalise_document(sag, upload_file):
                            upload_file.set_status(STATUS_CODE.SUCCESS, "File was uploaded successfully")
                            # break
                        else:
                            upload_file.set_status(STATUS_CODE.FAILED_TRY_AGAIN, "Failed to upload file, try again")
                    else:
                        # if i < times_to_try - 1:
                            # logger.info(f"Failed to find sag, try: {i+1}, will try again in {time_to_sleep} seconds")
                        # else:
                            # logger.info(f"Failed to find sag, try: {i+1}, will not try again")
                        upload_file.set_status(STATUS_CODE.FAILED_TRY_AGAIN, "No case found in SBSYS")
                        # i += 1
                        # time.sleep(time_to_sleep)
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
