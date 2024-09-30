from utils import SBSYSClient
import json
import logging


logger = logging.getLogger(__name__)


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

    def fetch_active_personalesager(self, cpr):
        try:
            if len(cpr) == 10:
                cpr = cpr[:6] + '-' + cpr[6:]  # Reformat the CPR

            # sag_search payload
            payload = {
                "PrimaerPerson": {
                    "CprNummer": cpr
                }
            }
            response = self.client.search_cases(payload)

            if not response:
                logger.info(f"sag_search response is None - No sager found for cpr: {cpr}")
                return None

            # Fetch the sag objects from 'Results' in response
            sager = response.get('Results', None)
            if not sager:
                logger.info(f"Results in sag_search is empty - No sager found for cpr: {cpr}")
                return None

            # Filter active sager by checking if SagsStatus.Navn is 'Aktiv'
            active_sager = [sag for sag in sager if sag.get('SagsStatus', {}).get('Navn') == 'Aktiv']

            if not active_sager:
                logger.info(f"No active sager found for cpr: {cpr}")
                return None

            # Filter personalesager based on KLE and FACET numbers starting with "81.03.00-G01"
            active_personalesager = [sag for sag in active_sager if sag.get('Nummer', '').startswith('81.03.00-G01')]

            if not active_personalesager:
                logger.info(f"No active personalesager found for cpr: {cpr}")
                return None

            return active_personalesager

        except Exception as e:
            logger.error(f"Error while fetching active personalesager: {e}")
            return None

    def fetch_delforloeb_files(self, sag_id: int, delforloeb_title: str, allowed_filetypes: list, document_keywords: list):
        try:
            # Fetch the list of delforloeb for a given sag
            delforloeb_list = self.client.get_request(path=f"api/delforloeb/sag/{sag_id}")
            if not delforloeb_list:
                logger.warning(f"No delforloeb found for sag id: {sag_id}")
                return None

            # Fetch the id of the delforloeb with 'Titel' matching the formal parameter delforloeb_title
            delforloeb_id = next(
                (item["ID"] for item in delforloeb_list if item.get("Titel") == delforloeb_title),
                None
            )

            # Check if delforloeb_id is None
            if not delforloeb_id:
                logger.warning(f"No delforloeb found with titel: {delforloeb_title}")
                return None

            # Fetch the delforloeb for a given delforloeb id
            delforloeb = self.client.get_request(path=f"api/delforloeb/{delforloeb_id}")

            # Check if delforloeb is None
            if not delforloeb:
                logger.warning(f"No delforloeb found with id: {delforloeb_id}")
                return None

            documents = delforloeb.get('Dokumenter', None)

            # Check if list of 'Dokumenter' is Empty
            if not documents:
                logger.info(f"No list of 'Dokumenter' found with delforloeb id: {delforloeb_id}")
                return None

            return documents

        except Exception as e:
            logger.error(f"Error during fetch_delforloeb_files: {e}")

    def journalise_file(self, sag, file, delforloeb_id, upload_id):
        try:
            sag_id = sag['Id']
            # Call the journalise_file_personalesag method with the JSON data
            json_data = {
                "json": f'{{"SagID": {sag_id}, "OmfattetAfAktindsigt": true, "DokumentNavn": "E-rekruttering – Ansættelsesdata", "DokumentArt": {{"Id": 1}}}}'
                # DokumentArt Id 1 = "Indgående" dokument art
            }

            # Prepare the files parameter as a dictionary
            files = {'file': (file.filename, file.stream, file.mimetype)}

            # Call the journalise_file_personalesag method and capture the response
            response = self.client.journalise_file_personalesag(json_data, files, delforloeb_id)

            logger.info(f"journalise_file response: {response}")

            # Check if the response is received
            if response:
                return response
            else:
                return None
        except Exception as e:
            print("An error occurred in journalise_file:", e)
            return None
