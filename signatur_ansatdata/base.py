"""
signatur_ansatdata base module.

This is the principal module of the signatur_ansatdata project.
here you put your main classes and objects.

Be creative! do whatever you want!

If you want to replace this with a Flask application run:

    $ make init

and then choose `flask` as template.
"""
import requests


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
        
    def post(self, path, data=None):
        return self._make_request(requests.post, path, json=data)
    
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
    def journalise_file_personalesag(self, query):
        path = "api/dokument/journaliser"
        return self.api_client.post(path, data={"query": query})


def hello_world():
    print("Hello, World!")