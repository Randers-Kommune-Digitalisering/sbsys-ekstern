from flask import Flask, jsonify, request
from request_validation import validate_request
from utils import SBSYSClient

app = Flask(__name__)

@app.route('/api/journaliser/fil', methods=['POST'])
def sbsys_journaliser_fil():
    # Check if request has JSON data
    if not request.is_json:
        return jsonify({"error": "Request must contain JSON data"}), 400

    data = request.json
    
    # Validate the request data
    validation_result, error_response = validate_request(data)

    if not validation_result:
        # Return the bad request error response
        return error_response, 400
       
    return jsonify({"success": "Data validated successfully"}), 200

def find_newest_personalesag(data):
    
    client = SBSYSClient(base_url="https://sbsysapi.randers.dk", api_key="")
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
    response = client.search_cases(json_data)

    if response:
        print("Search results:")
        print(response)
    else:
        print("Failed to retrieve search results")