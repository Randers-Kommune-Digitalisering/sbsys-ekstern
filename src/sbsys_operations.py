from utils import SBSYSClient


class SBSYSOperations:
    def __init__(self):
        self.client = SBSYSClient()

    def find_newest_personalesag(self, cpr):
        
        # Define your JSON data
        json_data = {
            "PrimaerPerson": {
                "CprNummer": cpr
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
        sag_id = sag['Id']
        # Call the journalise_file_personalesag method with the JSON data
        json_data = {
            "json": f'{{"SagID": {sag_id}, "OmfattetAfAktindsigt": true, "DokumentNavn": "Ansættelses Data"}}'
        }
        print("json_data: " + str(json_data))

        # Prepare the files parameter as a dictionary
        files = {'file': file}

        # Call the journalise_file_personalesag method and capture the response
        response = self.client.journalise_file_personalesag(json_data, files)

        # Check if the response is received
        if response:
            print("Response:", response)
            return response
        else:
            print("Failed to retrieve search results")
            return None
