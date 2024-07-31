import base64
import uuid
import requests
import base64
import time
import logging

from enum import Enum

from threading import Lock
from config import SBSYS_URL, SBSIP_URL, SBSYS_CLIENT_ID, SBSYS_CLIENT_SECRET, SBSYS_USERNAME, SBSYS_PASSWORD


logger = logging.getLogger(__name__)


class STATUS_CODE(Enum):
    FAILED = 0
    FAILED_TRY_AGAIN = 1
    RECEIVED = 2
    PROCESSING = 3
    SUCCESS = 4


class SignaturFileupload:
    def __init__(self, file, employment: str, cpr: str):
        self.file = file
        self.employment = employment
        self.cpr = cpr
        self.id = str(uuid.uuid4())  # Generate a unique ID as a string
        self.set_status(STATUS_CODE.RECEIVED, 'File upload received')  # Set the initial status to RECEIVED

    def __repr__(self):
        return f"<file:{self.file} employment:{self.employment} cpr:{self.cpr} id:{self.id}>"

    def get_id(self):
        return self.id
    
    def update_values(self, file, employment, cpr):
        self.file = file
        self.employment = employment
        self.cpr = cpr
        self.set_status(STATUS_CODE.RECEIVED, 'File upload updated')
    
    def set_status(self, status, message):
        self.status = status
        self.message = message
    
    def get_status(self):
        return self.status, self.message


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

    # journaliser fil
    def journalise_file_personalesag(self, data, files, delforloeb_id):
        path = "api/dokument/journaliser/" + str(delforloeb_id)        
        return self.api_client.post_upload(path, data=data, files=files)
    
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