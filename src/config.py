import os
from dotenv import load_dotenv


load_dotenv()


DEBUG = os.environ["DEBUG"]

# Keycloak
KEYCLOAK_URL = os.environ["KEYCLOAK_URL"]
KEYCLOAK_REALM = os.environ["KEYCLOAK_REALM"]
KEYCLOAK_CLIENT_ID = os.environ["KEYCLOAK_CLIENT_ID"]
KEYCLOAK_CLIENT_SECRET = os.environ["KEYCLOAK_CLIENT_SECRET"]
ADD_FILE_ROLE = os.environ["ADD_FILE_ROLE"]

# SBSYS
SBSYS_URL = os.environ["SBSYS_URL"]
SBSIP_URL = os.environ["SBSIP_URL"]
SBSYS_CLIENT_ID = os.environ["SBSYS_CLIENT_ID"]
SBSYS_CLIENT_SECRET = os.environ["SBSYS_CLIENT_SECRET"]
SBSYS_USERNAME = os.environ["SBSYS_USERNAME"]
SBSYS_PASSWORD = os.environ["SBSYS_PASSWORD"]