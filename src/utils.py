import base64
import requests
import base64
import sys
import time
import logging
import re

from werkzeug import serving

from config import SBSYS_URL, SBSIP_URL, SBSYS_CLIENT_ID, SBSYS_CLIENT_SECRET, SBSYS_USERNAME, SBSYS_PASSWORD, DEBUG
from database import SignaturFileupload, STATUS_CODE

logger = logging.getLogger(__name__)


def set_logging_configuration():
    log_level = logging.DEBUG if DEBUG else logging.INFO
    logging.basicConfig(stream=sys.stdout, level=log_level, format='[%(asctime)s] %(levelname)s - %(name)s - %(module)s:%(funcName)s - %(message)s', datefmt='%d-%m-%Y %H:%M:%S')
    disable_endpoint_logs(('/metrics', '/healthz'))


def disable_endpoint_logs(disabled_endpoints):
    parent_log_request = serving.WSGIRequestHandler.log_request

    def log_request(self, *args, **kwargs):
        if not any(re.match(f"{de}$", self.path) for de in disabled_endpoints):
            parent_log_request(self, *args, **kwargs)

    serving.WSGIRequestHandler.log_request = log_request


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
    msg = None
    if isinstance(upload, SignaturFileupload):
        status, message = upload.get_status()
        msg = {"id": upload.get_id(), "status_code": status.value, "status_text": status.name, "message": message} 
    elif received_id:
        msg = {"id": received_id, "status_code": STATUS_CODE.FAILED.value, "status_text": STATUS_CODE.FAILED.name, "message": message}
    else:
        msg = {"id": None, "status_code": STATUS_CODE.FAILED.value, "status_text": STATUS_CODE.FAILED.name, "message": message}

    logger.info(f"Response: {msg}")
    return msg, http_code
