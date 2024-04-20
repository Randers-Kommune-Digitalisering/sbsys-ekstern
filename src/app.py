from flask import Flask, jsonify, request
from request_validation import validate_request_journaliser_fil
from sbsys_operations import SBSYSOperations

sbsys_url = "https://sbsysapi.randers.dk"
token = ""
app = Flask(__name__)

@app.route('/api/journaliser/fil', methods=['POST'])
def sbsys_journaliser_fil():
    print("hello world")
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
    json_data = {
        "PrimaerPerson": {
            "CprNummer": request.json.get('cpr')
        },
        "SagsTyper": [
            {
            "Id": 5
            }
        ]
    }       
    sbsys = SBSYSOperations(sbsys_url, token)
    sag = sbsys.find_newest_personalesag(json_data)
    # TODO journaliser fil fra request på sagen fra find_newest_personalesag
    # TODO Hvordan skal filen journaliseres? delforløb, navn, type.
    return jsonify({"success": "Data validated successfully"}), 200


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8080)
