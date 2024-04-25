from flask import Flask, jsonify, request
from request_validation import validate_request_journaliser_fil
from sbsys_operations import SBSYSOperations
import requests, base64, os

# docker build -t signatur-ansatdata .
# docker run -d -p 8080:8080 signatur-ansatdata
app = Flask(__name__)

@app.route('/api/journaliser/fil', methods=['POST'])
def sbsys_journaliser_fil():

    # Check if request contains JSON data
    if not request.is_json:
        return jsonify({"error": "Request must contain JSON data"}), 400

    # Extract JSON data from request
    data = request.json

    # Validate the request
    validation_result, error_response = validate_request_journaliser_fil(data)
    if not validation_result:
        return jsonify(error_response), 400  # Return error response if validation fails

    # Find newest personalesag based on CPR from request
    sbsys = SBSYSOperations()
    sag = sbsys.find_newest_personalesag(data)
    
    # Check if sag is None
    if sag is None:
        return jsonify({"error": "Failed to retrieve search results based on given cpr"}), 500

    # Find delforloeb id for SBSYS sag
    delforloeb_array = sbsys.find_personalesag_delforloeb(sag)  # array with delforloeb
    mappe_id = None
    if "mappeId" in data["sagData"]:
        mappe_id = data["sagData"]["mappeId"]
    else:
        mappe_id = 0
    delforloeb_object_from_index = delforloeb_array[mappe_id]  # Select the delforloeb object based on index given from sataData['mappeId]
    delforloeb_id = delforloeb_object_from_index["ID"]  # Save the unique ID of the delforloeb object

    # Journalise file 
    fil = request.json.get('fil')
    binary_data = base64.b64decode(fil)
    response = sbsys.journalise_file(sag, binary_data, data, delforloeb_id)

    # Check if sag is None
    if response is None:
        return jsonify({"error": "Failed to journalise file, try again"}), 500

    print(response)

    # TODO journaliser fil fra request på sagen fra find_newest_personalesag
    # TODO Hvordan skal filen journaliseres? delforløb, navn, type.
    return jsonify({"success": "Fil uploaded successfully"}), 200

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8080)
