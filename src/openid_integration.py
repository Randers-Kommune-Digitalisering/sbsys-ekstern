import requests
import jwt
import logging
from functools import wraps
from cryptography.hazmat.primitives import serialization
from flask import Response, request
from base64 import b64decode


logger = logging.getLogger(__name__)


class AuthorizationHelper:
    def __init__(self, keycloak_url, realm, audience):
        self.algorithms = ["RS256"]
        self.audience = audience
        self.url = f"{keycloak_url}auth/realms/{realm}/"

        logging.error(self.audience)

        self.public_key = self.get_public_key()

    def get_public_key(self):
        try:
            r = requests.get(self.url)
            r.raise_for_status()
            key_der_base64 = r.json()["public_key"]
            key_der = b64decode(key_der_base64.encode())
            return serialization.load_der_public_key(key_der)
        except requests.exceptions.RequestException as e:
            return None
    
    def decode_token(self, token):
        logging.error(self.audience)
        try:
            if not self.public_key:
                self.public_key = self.get_public_key()
                if not self.public_key:
                    logging.error('No public key - cannot verify tokens')
                    return None

            payload = jwt.decode(token, self.public_key, audience=self.audience, algorithms=self.algorithms)
            logging.error(payload)
            return payload
        except jwt.ExpiredSignatureError:
            logging.error('Expired')
            return None
        except jwt.InvalidAudienceError:
            logging.error('Audience')
            return None
        except jwt.InvalidTokenError:
            logging.error('Invalid token')
            return None
    
    # Decorator - checks token
    def authorization(self, f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                token_header = request.headers.get('Authorization')
                print(token_header)
                if not token_header:
                    return Response(status=401, response="Unauthorized")
                else:
                    token = token_header.split()[1]
                    print(token)
                    if self.decode_token(token):
                        return f(*args, **kwargs)
                    else:
                        print("Decode token retunr nothing")
                        return Response(status=401, response="Unauthorized")
            except Exception as e:
                print(e)
                return Response(status=401, response=str(e))
        return decorated_function
