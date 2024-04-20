from flask import Flask, jsonify, request
from request_validation import validate_request_journaliser_fil
from sbsys_operations import SBSYSOperations
import requests, base64, os

# docker build -t signatur-ansatdata .
# docker run -d -p 8080:8080 signatur-ansatdata
sbsys_url = "https://sbsysapitest.randers.dk"
token = "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICIyZlR0cW5Hamo3M082bElzUmZDdlp4WHYtNjVva0I3WFZDNERRT2JnT3ZNIn0.eyJqdGkiOiJjNTgzNjg5Ny03Y2NhLTQ5ZjAtYTc4Yi1lYTJlODI3MGY5N2YiLCJleHAiOjE3MTM2NzI5MjIsIm5iZiI6MCwiaWF0IjoxNzEzNjQ0MTIyLCJpc3MiOiJodHRwczovL3Nic2lwLXdlYi10ZXN0MDEucmFuZGVycy5kazo4NTQzL2F1dGgvcmVhbG1zL3Nic2lwIiwiYXVkIjoicmFuZGVycy11ZHZpa2xpbmcta2xpZW50Iiwic3ViIjoiYzExNzEzYTItN2M5OC00NmY3LWFiOWItYmM0Y2MyYWViYjZlIiwidHlwIjoiQmVhcmVyIiwiYXpwIjoicmFuZGVycy11ZHZpa2xpbmcta2xpZW50IiwiYXV0aF90aW1lIjowLCJzZXNzaW9uX3N0YXRlIjoiNjE5NWEwYWUtODk0MC00ZjEwLThmZjItM2QzOWM1ODBlNzkyIiwiYWNyIjoiMSIsImNsaWVudF9zZXNzaW9uIjoiN2IxMzBmMDItMTc0My00YjViLWIzNTEtNDI2NWI0ZmU0OWI1IiwiYWxsb3dlZC1vcmlnaW5zIjpbXSwicmVhbG1fYWNjZXNzIjp7InJvbGVzIjpbInVtYV9hdXRob3JpemF0aW9uIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsiYWNjb3VudCI6eyJyb2xlcyI6WyJtYW5hZ2UtYWNjb3VudCIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwidmlldy1wcm9maWxlIl19fSwiYXVkIjoic2JzeXNhcGl0ZXN0LnJhbmRlcnMuZGsiLCJuYW1lIjoiIiwicHJlZmVycmVkX3VzZXJuYW1lIjoicGVyc29uYWxlc2FnZXIifQ.O1huehTbHj23W5KFnZCpSkUmVOorgRYQAlp8Mx5S3PZ3eJiPZzWHmo1n-RuzO7poQDPi4NMbo7uMV99uSbszgcubiXPK4wRx5ePzSxiiiEgrOxVlf73I44HmI6jTHtG7KMf-uqLG11hplVv9F5Kfml-1huwXERjAjVpGZCWQ68r-x5-Moq__JmClh6yq84-VOo8I8lL5FN_ONp6E61IMWvXrpFs2wTAeHX15k5qYPd0EceXkAIUN7BiSdI-kY8241BEQCx-NZACPH2XyzF-NVZvI0SUE9bCVr_VX0lFrZwyO1M22riwYGvq2UV6mQCS1bLuqicOBKxb19nvEOBIw9A"
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
    cpr = request.json.get('cpr')
    sbsys = SBSYSOperations(sbsys_url, token)
    sag = sbsys.find_newest_personalesag(cpr)
    
    # Check if sag is None
    if sag is None:
        return jsonify({"error": "Failed to retrieve search results based on given cpr"}), 500

    # Journalise file 
    fil = request.json.get('fil')
    binary_data = base64.b64decode(fil)

    response = sbsys.journalise_file(sag, binary_data)
    print(response)

    # TODO journaliser fil fra request på sagen fra find_newest_personalesag
    # TODO Hvordan skal filen journaliseres? delforløb, navn, type.
    return jsonify({"success": "Fil uploaded successfully"}), 200


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8080)
