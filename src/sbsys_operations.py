from utils import SBSYSClient

class SBSYSOperations:
    def __init__(self, base_url, api_key):
        self.client = SBSYSClient(base_url=base_url, api_key=api_key)

    def find_newest_personalesag(self, data):
        
        # Define your JSON data
        json_data = {
            "PrimaerPerson": {
                "CprNummer": "200395-xxxx"
            },
            "SagsTyper": [
                {
                    "Id": 5
                }
            ]
        }

        # Call the journalise_file_personalesag method with the JSON data
        response = self.client.search_cases(data)
        
        if response:
            print("Search results:" + str(response))
            latest_object = max(response['Results'], key=lambda x: x['Oprettet'])
            print("Latest sag: " + str(latest_object))
        else:
            print("Failed to retrieve search results")

