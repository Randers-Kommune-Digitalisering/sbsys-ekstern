from flask import Flask, jsonify, request
from healthcheck import HealthCheck
from request_validation import is_cpr, is_pdf
from sbsys_operations import SBSYSOperations


app = Flask(__name__)

health = HealthCheck()
sbsys = SBSYSOperations()

app.add_url_rule("/healthz", "healthcheck", view_func=lambda: health.run())

@app.route('/api/journaliser/ansattelse/fil', methods=['POST'])
def sbsys_journaliser_ansattelse_fil():
    # Get form data
    cpr = request.form.get('cpr', None)
    file = request.files.get('file', None)

    if cpr and file:
        if not is_cpr(cpr):
            return jsonify({"error": "Not a valid cpr number"}), 400
        
        # TODO: Kun PDF filer? eller skal det være muligt at tilføje tekst filer?
        if not is_pdf(file):
            return jsonify({"error": "Not a valid PDF file"}), 400

        # Find newest personalesag based on CPR from request
        sag = sbsys.find_newest_personalesag({"cpr":cpr, "sagType": {"Id": 5}})
        
        # Check if sag is None
        if sag is None:
            return jsonify({"error": "Failed to find case based on given cpr"}), 400

        delforloeb_array = sbsys.find_personalesag_delforloeb(sag)
        if len(delforloeb_array) < 1:
            return jsonify({"error": "Failed to find delforløb, try again"}), 500
        
        delforloeb_object_from_index = delforloeb_array[0]  # Select the first delforloeb object 
        delforloeb_id = delforloeb_object_from_index["ID"]  # Save the unique ID of the delforloeb object

        # Journalise file 
        response = sbsys.journalise_file(sag, file, delforloeb_id)

        # Check if sag is None
        if response is None:
            return jsonify({"error": "Failed to journalise file, try again"}), 500

        #print(response)

        # TODO Hvordan skal filen journaliseres? delforløb, navn, type.
        return jsonify({"success": "File uploaded successfully"}), 200
    
    return jsonify({"error": "Missing parameter, must contain cpr and file"}), 400


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8080)
