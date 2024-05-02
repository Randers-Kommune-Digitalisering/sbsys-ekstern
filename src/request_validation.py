from werkzeug.datastructures import FileStorage
from utils import convert_filestring_to_bytes


def is_cpr(cpr):
    if not (len(cpr) == 10 and cpr.isdigit()) and not (len(cpr) == 11 and cpr[:6].isdigit() and cpr[6] == '-' and cpr[7:].isdigit()):
        return False
    return True

def is_pdf(file):
    if isinstance(file, FileStorage):
        return file.mimetype == 'application/pdf' and file.filename.split('.')[-1].lower()  == 'pdf'
    return False

def validate_file(filestring):
     return convert_filestring_to_bytes(filestring).startswith(b'%PDF')


# validate the request where False output should result in a Bad Request response
def validate_request_journaliser_fil(data):  
    # Check if 'cpr', 'fil', and 'sagType' keys exist
    if not all(key in data for key in ['cpr', 'fil', 'sagType']):
        return False, {"error": "Request must contain 'cpr', 'fil', 'sagType' keys"}

    # Validate 'cpr' format
    cpr = str(data.get('cpr', ''))  # Convert to string
    if not (len(cpr) == 10 and cpr.isdigit()) and not (len(cpr) == 11 and cpr[:6].isdigit() and cpr[6] == '-' and cpr[7:].isdigit()):
        return False, {"error": "Invalid format for 'cpr'. It should be digits in either 'xxxxxxxxxx' or 'xxxxxx-xxxx' format"}

    # Check 'sagType' format
    sag_type = data.get('sagType')
    if not isinstance(sag_type, dict) or 'Id' not in sag_type or not isinstance(sag_type['Id'], int) or sag_type['Id'] != 5:
        return False, {
            "error": "Invalid format or unknown id for 'sagType'. It should be a dictionary with an 'Id' key, e.g., {'Id': 0}"}

    # Check 'sagData' format
    sag_data = data.get('sagData')
    if (isinstance(sag_data, dict) and 'dokumentNavn' not in sag_data
            or not isinstance(sag_data['dokumentNavn'], str)):
        return False, {
            "error": "sagData must contain 'dokumentNavn' key and optionally a 'mappeId' key. e.g. {'dokumentNavn': 'text', 'mappeId: 0}"
        }

    # Validate CPR value
    # if not validate_cpr(cpr):
    #    return False, {"error": "Der eksisterer ingen personalesager på dette CPR"}

     # Validate file format
    fil = data.get('fil', '')
    file_bytes, file_error = convert_filestring_to_bytes(fil)
    if not file_bytes:
        return False, file_error
    
    return True, None
