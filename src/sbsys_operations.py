from utils import SBSYSClient

class SBSYSOperations:
    def __init__(self, base_url, api_key):
        self.client = SBSYSClient(base_url=base_url, api_key=api_key)

    def find_newest_personalesag(self, data):
        
        # Define your JSON data
        json_data = {
            "PrimaerPerson": {
                "CprNummer": data
            },
            "SagsTyper": [
                {
                "Id": 5
                }
            ]
        } 

        # Call the search cases method with the JSON data
        response = self.client.search_cases(json_data)
        
        if response:
            print("Search results:" + str(response))
            latest_object = max(response['Results'], key=lambda x: x['Oprettet'])
            print("Latest sag: " + str(latest_object))
            return latest_object
        else:
            print("Failed to retrieve search results")
            print(response)
            return None

    def journalise_file(self, sag, file):
        sagID = sag['Id']
        # Call the journalise_file_personalesag method with the JSON data
        json_data = {
            "json": '{"SagID": ' + str(sagID) + ',"OmfattetAfAktindsigt": true,"DokumentNavn": "Ansættelses Data"}'
        }

        # Prepare the files parameter as a dictionary
        files = {'file': file}

        # Call the journalise_file_personalesag method and capture the response
        response = self.client.journalise_file_personalesag(sag, json_data, files)

        # Check if the response is received
        if response:
            print("Response:", response)
            return response
        else:
            print("Failed to retrieve search results")
            return None
