import base64

def validate_cpr(cpr):
    return True

def validate_file(filestring):
     return convert_filestring_to_bytes(filestring).startswith(b'%PDF')

# Convert a base64 encoded string to file
def convert_filestring_to_bytes(file_string):
    try:
        # Decode base64 string
        decoded_bytes = base64.b64decode(file_string, validate=True)
        
        # Check if the decoded bytes start with the PDF magic number
        if decoded_bytes.startswith(b'%PDF'):
            return decoded_bytes, None
        else:
            return None, {"error": "File must be a PDF"}
    except Exception as e:
        # If an error occurs during decoding or validation, return an error message
        print(f"Error decoding base64 string: {e}")
        return None, {"error": "File is not valid. Make sure it is a base64 encoded filestring"}

# validate the request where False results in a Bad Request response
def validate_request_journaliser_fil(data):  
    # Check if 'cpr', 'fil', and 'sagType' keys exist
    if not all(key in data for key in ['cpr', 'fil', 'sagType']):
        return False, {"error": "Request must contain 'cpr', 'fil', and 'sagType' keys"}

    # Validate 'cpr' format
    cpr = str(data.get('cpr', ''))  # Convert to string
    if not (len(cpr) == 10 and cpr.isdigit()) and not (len(cpr) == 11 and cpr[:6].isdigit() and cpr[6] == '-' and cpr[7:].isdigit()):
        return False, {"error": "Invalid format for 'cpr'. It should be digits in either 'xxxxxxxxxx' or 'xxxxxx-xxxx' format"}

    # Check 'sagType' format
    sag_type = data.get('sagType')
    if not isinstance(sag_type, dict) or 'Id' not in sag_type or not isinstance(sag_type['Id'], int) or sag_type['Id'] != 0:
        return False, {"error": "Invalid format for 'sagType'. It should be a dictionary with an 'Id' key, e.g., {'Id': 0}"}
    
    # Validate CPR value
    if not validate_cpr(cpr):
        return False, {"error": "Der eksisterer ingen personalesager på dette CPR"}

     # Validate file format
    fil = data.get('fil', '')
    file_bytes, file_error = convert_filestring_to_bytes(fil)
    if not file_bytes:
        return False, file_error
    
    return True, None
