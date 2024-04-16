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
        return decoded_bytes
    except Exception as e:
        # If an error occurs during decoding or validation, return False
        print(f"Error decoding base64 string: {e}")
        return False

# validate the request where False results in a Bad Request response
def validate_request(data):
    # Check if 'cpr', 'fil', and 'sagType' keys exist
    if not all(key in data for key in ['cpr', 'fil', 'sagType']):
        return False, {"error": "Request must contain 'cpr', 'fil', and 'sagType' keys"}

    # Check 'cpr' format
    cpr = data.get('cpr', '')
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
    if not validate_file(fil):
        return False, {"error": "File must be .pdf"}
    
    return True, None
