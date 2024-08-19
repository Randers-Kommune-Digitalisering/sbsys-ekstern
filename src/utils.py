import base64
import requests
import base64
import time
import logging

from config import SBSYS_URL, SBSIP_URL, SBSYS_CLIENT_ID, SBSYS_CLIENT_SECRET, SBSYS_USERNAME, SBSYS_PASSWORD
from database import SignaturFileupload, STATUS_CODE

logger = logging.getLogger(__name__)


# Håndtering af http request
class APIClient:
    def __init__(self, sbsys_url, sbsip_url, client_id, client_secret, username, password):
        self.sbsys_url = sbsys_url
        self.sbsip_url = sbsip_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self.access_token = None
        self.token_expiry = None

    def authenticate(self):
        sbsip_url = f"{self.sbsip_url}/auth/realms/sbsip/protocol/openid-connect/token"
        json_data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": self.username,
            "password": self.password
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        try:
            response = requests.post(sbsip_url, headers=headers, data=json_data)
            response.raise_for_status()
            data = response.json()
            self.access_token = data['access_token']
            self.token_expires = time.time() + data['expires_in']
            return self.access_token
        except requests.exceptions.RequestException as e:
            logging.error(e)

    def get_access_token(self):
        # Check if there is a valid access token and it hasn't expired yet
        if self.access_token and self.token_expiry and time.time() < self.token_expiry:
            return self.access_token
        return self.authenticate()

    def _make_request(self, method, path, **kwargs):
        token = self.get_access_token()
        url = f"{self.sbsys_url}/{path}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Check if files are present in kwargs
        if 'files' in kwargs:
            # If files are present, remove Content-Type header
            headers.pop('Content-Type', None)

        try:
            response = method(url, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(e)
            return None

    def get(self, path):
        return self._make_request(requests.get, path)

    def post_upload(self, path, data=None, files=None):
        return self._make_request(requests.post, path, data=data, files=files)

    def post(self, path, data=None):
        return self._make_request(requests.post, path, json=data)

    def put(self, path, data=None):
        return self._make_request(requests.put, path, data=data, json=data)

    def delete(self, path):
        return self._make_request(requests.delete, path)
    
# Samling af sbsys requests
class SBSYSClient:
    def __init__(self):
        self.api_client = APIClient(SBSYS_URL, SBSIP_URL, SBSYS_CLIENT_ID, SBSYS_CLIENT_SECRET, SBSYS_USERNAME, SBSYS_PASSWORD)

    # søg efter sager
    def search_cases(self, body):
        path = "api/sag/search"
        return self.api_client.post(path, data=body)

    def get_sag_delforloeb(self, sag):
        path = "api/sag/" + str(sag["Id"]) + "/delforloeb"
        return self.api_client.get(path)

    def get_request(self, path):
        return self.api_client.get(path)

    def post_request(self, path, data=None, json=None):
        return self.api_client.post(path, data, json)

    def put_request(self, path, data=None, json=None):
        return self.api_client.put(path, data, json)

    def delete_request(self, path):
        return self.api_client.delete(path)

    # journaliser fil
    def journalise_file_personalesag(self, data, files, delforloeb_id):
        path = "api/dokument/journaliser/" + str(delforloeb_id)        
        return self.api_client.post_upload(path, data=data, files=files)

    def fetch_documents(self, sag_id):
        path = f"api/sag/{sag_id}/dokumenter"
        return self.api_client.get(path=path)

    
# Convert a base64 encoded string to file
def convert_filestring_to_bytes(file_string):
    try:
        # Decode base64 string
        decoded_bytes = base64.b64decode(file_string, validate=True)
        
        # Check if the decoded bytes start with the PDF magic number
        if decoded_bytes.startswith(b'%PDF'):
            return decoded_bytes, None
        else:
            return None, {"error": "File must be a PDF"}
    except Exception as e:
        # If an error occurs during decoding or validation, return an error message
        print(f"Error decoding base64 string: {e}")
        return None, {"error": "File is not valid. Make sure it is a base64 encoded filestring"}


def generate_response(message: str, http_code: int, upload=None, received_id=None):
    if isinstance(upload, SignaturFileupload):
        status, message = upload.get_status()
        return {"id": upload.get_id(), "status_code": status.value, "status_text": status.name, "message": message}, http_code
    elif received_id:
        return {"id": received_id, "status_code": STATUS_CODE.FAILED.value, "status_text": STATUS_CODE.FAILED.name, "message": message}, http_code
    else:
        return {"id": None, "status_code": STATUS_CODE.FAILED.value, "status_text": STATUS_CODE.FAILED.name, "message": message}, http_code


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


def xml_to_json(xml_data):
    try:
        # Parse the XML data into a dictionary
        dict_data = xmltodict.parse(xml_data)
        return dict_data
    except Exception as e:
        logger.error(f"An error occurred while converting XML to JSON: {e}")
        return None