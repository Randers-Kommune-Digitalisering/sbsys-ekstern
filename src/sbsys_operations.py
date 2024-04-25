from utils import SBSYSClient
import json


class SBSYSOperations:
    def __init__(self):
        self.client = SBSYSClient()

    def find_newest_personalesag(self, data):

        # Reformat cpr key if neccessary
        cpr = data["cpr"]
        if len(cpr) == 10:
            cpr = cpr[:6] + "-" + cpr[6:]

        # JSON data for search_cases
        json_data = {
            "PrimaerPerson": {
                "CprNummer": cpr
            },
            "SagsTyper": [
                {
                "Id": data["sagType"]["Id"]
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

    def find_personalesag_delforloeb(self, sag):

        # Call the journalise_file_personalesag method and capture the response
        response = self.client.get_sag_delforloeb(sag)

        # Check if the response is received
        if response:
            print("Response:", response)
            return response
        else:
            print("Failed to retrieve search results")
            return None

    def journalise_file(self, sag, file, data, delforloeb_id):
        sag_id = sag['Id']
        # Call the journalise_file_personalesag method with the JSON data
        navn = "file"
        if data["sagData"]["dokumentNavn"]:
            navn = data["sagData"]["dokumentNavn"]
        json_data = {
            "json": f'{{"SagID": {sag_id}, "OmfattetAfAktindsigt": true, "DokumentNavn": "{navn}", "DokumentArt": {{"Id": 1}}}}'  # DokumentArt Id 1 = "Indgående" dokument art
        }
        print("json_data: " + str(json_data))

        # Prepare the files parameter as a dictionary
        files = {'file': file}

        # Call the journalise_file_personalesag method and capture the response
        response = self.client.journalise_file_personalesag(json_data, files, delforloeb_id)

        # Check if the response is received
        if response:
            print("Response:", response)
            return response
        else:
            print("Failed to retrieve search results")
            return None
