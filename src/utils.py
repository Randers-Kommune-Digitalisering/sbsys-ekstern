import requests, base64


# Håndtering af http request
class APIClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key

    def _make_request(self, method, path, **kwargs):
        url = f"{self.base_url}/{path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = method(url, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return None

    def get(self, path):
        return self._make_request(requests.get, path)

    def post(self, path, data=None, files=None):
        return self._make_request(requests.post, path, json=data, files=files)

    def put(self, path, data=None):
        return self._make_request(requests.put, path, json=data)

    def delete(self, path):
        return self._make_request(requests.delete, path)
    
# Samling af sbsys requests
class SBSYSClient:
    def __init__(self, base_url, api_key):
        self.api_client = APIClient(base_url, api_key)

    # søg efter sager
    def search_cases(self, body):
        path = "api/sag/search"
        return self.api_client.post(path, data=body)

    # journaliser fil
    def journalise_file_personalesag(self, sag, data, files):

        path = "api/dokument/journaliser/" + "421"
        return self.api_client.post(path, data=data, files=files)
    
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
