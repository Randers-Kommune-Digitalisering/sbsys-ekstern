from utils import SBSYSClient
import json


class SBSYSOperations:
    def __init__(self):
        self.client = SBSYSClient()

    def find_newest_personalesag(self, data):
        try:
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

            # Call the search_cases method with the JSON data
            response = self.client.search_cases(json_data)

            # Handle Empty response
            if not response:
                return None

            # Filter active cases (SagsStatus Id == 6)
            active_cases = [case for case in response['Results'] if case['SagsStatus']['Navn'] == 'Aktiv']
            
            # Handle no active cases
            if not active_cases:
                return None

            # Find the latest active case
            latest_active_case = max(active_cases, key=lambda x: x['Oprettet'])

            return latest_active_case

        except Exception as e:
            print("An error occurred in find_newest_personalesag:", e)
            return None

    def find_personalesag_delforloeb(self, sag):
        try:
            # Call the journalise_file_personalesag method and capture the response
            response = self.client.get_sag_delforloeb(sag)

            # Check if the response is received
            if response:
                return response
            else:
                return None
        except Exception as e:
            print("An error occurred in find_personalesag_delforloeb:", e)
            return None

    def journalise_file(self, sag, file, delforloeb_id, upload_id):
        try:
            sag_id = sag['Id']
            # Call the journalise_file_personalesag method with the JSON data
            json_data = {
                "json": f'{{"SagID": {sag_id}, "OmfattetAfAktindsigt": true, "DokumentNavn": "E-recruttering - Ansættelsesdata - {upload_id}", "DokumentArt": {{"Id": 1}}}}'
                # DokumentArt Id 1 = "Indgående" dokument art
            }

            # Prepare the files parameter as a dictionary
            files = {'file': (file.filename, file.stream, file.mimetype)}

            # Call the journalise_file_personalesag method and capture the response
            response = self.client.journalise_file_personalesag(json_data, files, delforloeb_id)

            # Check if the response is received
            if response:
                return response
            else:
                return None
        except Exception as e:
            print("An error occurred in journalise_file:", e)
            return None
