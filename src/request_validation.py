from utils import convert_filestring_to_bytes

def validate_cpr(cpr):
    return True

def validate_file(filestring):
     return convert_filestring_to_bytes(filestring).startswith(b'%PDF')


# validate the request where False results in a Bad Request response
def validate_request_journaliser_fil(data):  
    # Check if 'cpr', 'fil', and 'sagType' keys exist
    if not all(key in data for key in ['cpr', 'fil']):
        return False, {"error": "Request must contain 'cpr' and 'fil' keys"}

    # Validate 'cpr' format
    cpr = str(data.get('cpr', ''))  # Convert to string
    if not (len(cpr) == 10 and cpr.isdigit()) and not (len(cpr) == 11 and cpr[:6].isdigit() and cpr[6] == '-' and cpr[7:].isdigit()):
        return False, {"error": "Invalid format for 'cpr'. It should be digits in either 'xxxxxxxxxx' or 'xxxxxx-xxxx' format"}

    # Validate CPR value
    if not validate_cpr(cpr):
        return False, {"error": "Der eksisterer ingen personalesager på dette CPR"}

     # Validate file format
    fil = data.get('fil', '')
    file_bytes, file_error = convert_filestring_to_bytes(fil)
    if not file_bytes:
        return False, file_error
    
    return True, None
