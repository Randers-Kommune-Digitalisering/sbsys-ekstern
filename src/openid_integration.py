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

#access_token = "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICI2a09FeDhzVFozdVhjcFJFa3pyTG5qWkc2eWhiWFJ5Q2c0Z2J2eG45cDdrIn0.eyJleHAiOjE3MTQwMzEwOTcsImlhdCI6MTcxNDAzMDc5NywianRpIjoiYzc4OGYxMTctZWIzOC00YzU1LWFlNDEtNGZkNTViMGY0Njc2IiwiaXNzIjoiaHR0cDovL2xvY2FsaG9zdDo4MDgwL3JlYWxtcy9yYW5kZXJzLWtvbW11bmUiLCJhdWQiOiJhY2NvdW50Iiwic3ViIjoiZmZiNzA4MTYtMmRiMC00ZjczLThjNzctMThmMTRiYWZmMjVmIiwidHlwIjoiQmVhcmVyIiwiYXpwIjoic2JzeXMtZWtzdGVybiIsInNlc3Npb25fc3RhdGUiOiJiOTczYTdjMC01NWYwLTQ1YmUtODM4OS0yY2U0YjkxN2YwZTgiLCJyZWFsbV9hY2Nlc3MiOnsicm9sZXMiOlsiZGVmYXVsdC1yb2xlcy10ZXN0Iiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiJdfSwicmVzb3VyY2VfYWNjZXNzIjp7InNic3lzLWVrc3Rlcm4iOnsicm9sZXMiOlsiYWRkX3N0YWZmX2ZpbGUiXX0sImFjY291bnQiOnsicm9sZXMiOlsibWFuYWdlLWFjY291bnQiLCJtYW5hZ2UtYWNjb3VudC1saW5rcyIsInZpZXctcHJvZmlsZSJdfX0sInNjb3BlIjoib3BlbmlkIiwic2lkIjoiYjk3M2E3YzAtNTVmMC00NWJlLTgzODktMmNlNGI5MTdmMGU4In0.cHHJEl5KQNisGElJuVt1UCXOipAoppCfksaZOrgCEnHYmHCu35pSeV-KtImsyuUqAANrC_a2fAAB3BXpdYnWV3ReUKelnXWZ5Ihgfy19kRQrEG9labS3DYmCSxGakVQKZd6xH3doDYDP4iqFqO7DWHjHRQHoX8gOH8txVkfhOYkLs-gREKeuEpGTlOuuSaL-n9mg5Jr2Yg6FryE4ZhZ23L-9ZyYDt_5yzsHRzlpB2NnjWpXMBOQE3kM64zVntvU6PleLknoMbCtWIzX7C9JLUEGHhDqOiX9ALF1kqtESpC_aUOAWSDYNmgc0auNC9Ry5wHpyyR-FygifWo4WRJUBhg"
