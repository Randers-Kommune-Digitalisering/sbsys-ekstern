import requests, base64, json, time

# Håndtering af http request
class APIClient:
    def __init__(self):
        self.sbsys_url = "https://sbsysapitest.randers.dk"
        self.sbsip_url = "https://sbsip-web-test01.randers.dk:8543"
        self.client_id = "randers-udvikling-klient"
        self.client_secret = "ada62743-4120-4b48-bd91-10ec5b7bc907"
        self.username = "Personalesager"
        self.password = "Randers1234"
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
            print("Error:", e)

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
            print(f"Error: {e}")
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
        self.api_client = APIClient()

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
