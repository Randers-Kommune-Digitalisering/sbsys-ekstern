import logging
import time
import requests
import xmltodict
import json
from datetime import datetime
from requests.auth import HTTPBasicAuth
from typing import Dict, Tuple, Optional
from base_api_client import BaseAPIClient


logger = logging.getLogger(__name__)


# Sbsys Api Client
class SDAPIClient(BaseAPIClient):
    _client_cache: Dict[Tuple[str, str], 'SDAPIClient'] = {}

    def __init__(self, username, password, url):
        super().__init__(url)
        self.username = username
        self.password = password

    @classmethod
    def get_client(cls, username, password, url):
        key = (username, password)
        if key in cls._client_cache:
            return cls._client_cache[key]
        client = cls(username, password, url)
        cls._client_cache[key] = client
        return client

    def authenticate(self):
        return HTTPBasicAuth(self.username, self.password)

    def get_headers(self):
        return {"Content-Type": "application/xml"}

    def _make_request(self, method, path, **kwargs):
        # Override _make_request to handle specific behavior for SDAPIClient
        try:
            response = super()._make_request(method, path, **kwargs)

            # Ensure we have a proper response object
            if not isinstance(response, requests.Response):
                logger.error(f"Expected a Response object, but got {type(response)}. Path: {path}")
                return None

            if not response:
                logger.error(f"Response is None. path: {path}")
                return None

            # Get the content type of the response
            content_type = kwargs.get('headers', {}).get('Content-Type', response.headers.get('Content-Type', ''))

            # Check if the response is HTML or XML
            if 'text/html' in content_type:
                return None
            elif 'application/xml' in content_type or 'text/xml' in content_type:
                # Handle XML response
                try:
                    response_dict = xml_to_json(response.content)
                    # Check for SOAP Fault in the response
                    fault = response_dict.get('Envelope', {}).get('Body', {}).get('Fault', None)
                    if fault:
                        fault_code = fault.get('faultcode', 'No fault code')
                        fault_string = fault.get('faultstring', 'No fault string')
                        fault_actor = fault.get('faultactor', 'No fault actor')
                        fault_detail = fault.get('detail', {}).get('string', 'No fault detail')
                        logger.error(
                            f"SOAP Fault occurred: Code: {fault_code}, String: {fault_string}, Actor: {fault_actor}, Detail: {fault_detail}")
                        return None

                    return response_dict
                except Exception as e:
                    logger.error(f"An error occurred while parsing the XML response: {e}")
                    return None
            else:
                logger.warning("Received a response that is neither HTML nor XML.")
                return None

        except requests.RequestException as e:
            logger.error(f"An error occurred while making the request: {e}")
            return None


class SDClient:
    def __init__(self, username, password, url):
        self.api_client = SDAPIClient.get_client(username, password, url)
        self.auth = self.api_client.authenticate()

    def get_request(self, path: str, params: Optional[Dict[str, str]] = None):
        try:
            response = self.api_client.get(path, auth=self.auth, params=params)
            return response
        except Exception as e:
            logger.error(f"An error occurred while perform get_request: {e}")

    def post_request(self, path: str, data=None, json=None, params: Optional[Dict[str, str]] = None):
        try:
            response = self.api_client.post(path, data=data, json=json, auth=self.auth, params=params)
            return response
        except Exception as e:
            logger.error(f"An error occurred while perform post_request: {e}")

    def put_request(self, path: str, data=None, json=None, params: Optional[Dict[str, str]] = None):
        try:
            response = self.api_client.put(path, data=data, json=json, auth=self.auth, params=params)
            return response
        except Exception as e:
            logger.error(f"An error occurred while perform put_request: {e}")

    def delete_request(self, path: str, params: Optional[Dict[str, str]] = None):
        try:
            response = self.api_client.delete(path, auth=self.auth, params=params)
            return response
        except Exception as e:
            logger.error(f"An error occurred while perform delete_request: {e}")

    def GetEmployment20111201(self, cpr, employment_identifier, inst_code, effective_date = None):
        path = 'GetEmployment20111201'

        if not effective_date:
            # Get the current date and format it as DD.MM.YYYY
            effective_date = datetime.now().strftime('%d.%m.%Y')

        # Define the SD params
        params = {
            'InstitutionIdentifier': inst_code,
            'EmploymentStatusIndicator': 'true',
            'PersonCivilRegistrationIdentifier': cpr,
            'EmploymentIdentifier': employment_identifier,
            'DepartmentIdentifier': '',
            'ProfessionIndicator': 'false',
            'DepartmentIndicator': 'true',
            'WorkingTimeIndicator': 'false',
            'SalaryCodeGroupIndicator': 'false',
            'SalaryAgreementIndicator': 'false',
            'StatusActiveIndicator': 'true',
            'StatusPassiveIndicator': 'true',
            'submit': 'OK',
            'EffectiveDate': effective_date
        }

        try:
            response = self.get_request(path=path, params=params)

            if not response:
                logger.warning("No response from SD client")
                return None

            if not response['GetEmployment20111201']:
                logger.warning("GetEmployment20111201 object not found")
                return None

            person_data = response['GetEmployment20111201'].get('Person', None)
            if not person_data:
                logger.warning(f"No employment data found for cpr: {cpr}")
                return None

            if isinstance(person_data, dict):
                person_data = [person_data]

            for person in person_data:
                employment = person.get('Employment', None)
                if not employment:
                    logger.warning(f"Person has no employment object: {person} ")
                    return None
                return employment
        except Exception as e:
            logger.error(f"An error occured GetEmployment20111201: {e}")

    def fetch_institutions_and_departments(self, region_identifier):
        inst_and_dep = []
        # Get institutions
        path = 'GetInstitution20080201'
        try:
            params = {
                'RegionIdentifier': region_identifier
            }
            logger.info("Fetching SD institutions...")
            response = self.post_request(path=path, params=params)

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
            logger.info("Fetching SD institutions success")
            # Get departments
            path = 'GetDepartment20080201'
            date_today = datetime.now().strftime('%d.%m.%Y')
            logger.info("Fetching SD departments...")
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

                response = self.post_request(path=path, params=params)

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
            logger.info("Fetching SD departments success")
            return inst_and_dep

        except Exception as e:
            logger.error(f"Error while fetching inst and departments: {e} \n"
                         f"Region code: {region_identifier}")
            return []

    def fetch_departments(self, inst_identifier):
        inst_and_dep = []
        try:
            # Get departments
            path = 'GetDepartment20080201'
            date_today = datetime.now().strftime('%d.%m.%Y')
            logger.info("Fetching SD departments...")

            if not inst_identifier:
                logger.warning("InstitutionIdentifier is None")
                return
            # Define the SD params
            params = {
                'InstitutionIdentifier': inst_identifier,
                'ActivationDate': date_today,
                'DeactivationDate': date_today,
                'DepartmentNameIndicator': 'true'
            }

            response = self.post_request(path=path, params=params)

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

            inst_and_dep_dict = {'InstitutionIdentifier': inst_identifier,
                                 'Department': department_list}
            inst_and_dep.append(inst_and_dep_dict)
            logger.info("Fetching SD departments success")
            return inst_and_dep

        except Exception as e:
            logger.error(f"Error while fetching inst and departments: {e} \n"
                         f"Institution identifier: {inst_identifier}")
            return []


def xml_to_json(xml_data):
    try:
        # Parse the XML data into a dictionary
        dict_data = xmltodict.parse(xml_data)
        return dict_data
    except Exception as e:
        logger.error(f"An error occurred while converting XML to JSON: {e}")
        return None
