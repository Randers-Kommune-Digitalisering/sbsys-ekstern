import json

from functools import wraps
from keycloak import KeycloakOpenID, exceptions as keycloak_exceptions
from flask import Response, request


class AuthorizationHelper:
    def __init__(self, server_url, realm, client_id, client_secret):
        self.keycloak_openid = KeycloakOpenID(server_url=server_url, client_id=client_id, realm_name=realm, client_secret_key=client_secret)
        self.client_id = client_id

    # Returns status code and response
    def get_token(self, username, password):
        try:
            token = self.keycloak_openid.token(username, password)
            token_info = self.keycloak_openid.introspect(token['access_token'])
            if 'sbsys-ekstern' in token_info['resource_access']:
                return 200, json.dumps(token)
            else:
                raise keycloak_exceptions.KeycloakAuthenticationError(b'{"error":"invalid_resource_access","error_description":"User does not have access to this resource"}', 401)
        except keycloak_exceptions.KeycloakAuthenticationError as e:
            return e.response_code, e.error_message
    
    # Returns status code and response
    def refresh_token(self, refresh_token):
        try:
            token = self.keycloak_openid.refresh_token(refresh_token)
            return 200, json.dumps(token)
        except keycloak_exceptions.KeycloakPostError as e:
            return e.response_code, e.error_message
    
    # Returns status code and response
    def logout(self, refresh_token):
        try:
            self.keycloak_openid.logout(refresh_token)
            return 200, "logout successful"
        except keycloak_exceptions.KeycloakPostError as e:
            return e.response_code, e.error_message

    # Returns True/False
    def has_role(self, access_token, role):
        token_info = self.keycloak_openid.introspect(access_token)
        if token_info['active']:
            if self.client_id in token_info['resource_access']:
                print(token_info['resource_access'][self.client_id]['roles'])
                return role in token_info['resource_access'][self.client_id]['roles']
        return False

    # Decorator - checks token and role
    def authorization(self, role):
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                try:
                    token_header = request.headers.get('Authorization')
                    if not token_header:
                        return Response(status=401, response="Unauthorized")
                    else:
                        token = token_header.split()[1]
                        if self.has_role(token, role):
                            return f(*args, **kwargs)
                        else:
                            return Response(status=401, response="Unauthorized")
                except Exception as e:
                    return Response(status=401, response=str(e))
            return decorated_function
        return decorator
