import os
from dotenv import load_dotenv


load_dotenv()


DEBUG = os.environ["DEBUG"].strip()

# Keycloak
KEYCLOAK_URL = os.environ["KEYCLOAK_URL"].strip()
KEYCLOAK_REALM = os.environ["KEYCLOAK_REALM"].strip()
KEYCLOAK_AUDIENCE = os.environ["KEYCLOAK_AUDIENCE"].strip()

# SBSYS
SBSYS_URL = os.environ["SBSYS_URL"].strip()
SBSIP_URL = os.environ["SBSIP_URL"].strip()
SBSYS_CLIENT_ID = os.environ["SBSYS_CLIENT_ID"].strip()
SBSYS_CLIENT_SECRET = os.environ["SBSYS_CLIENT_SECRET"].strip()
SBSYS_USERNAME = os.environ["SBSYS_USERNAME"].strip()
SBSYS_PASSWORD = os.environ["SBSYS_PASSWORD"].strip()

# Database
DB_NAME = os.environ["DB_NAME"].strip()
DB_USER = os.environ["DB_USER"].strip()
DB_PASSWORD = os.environ["DB_PASSWORD"].strip()
DB_HOST = os.environ["DB_HOST"].strip()
DB_PORT = os.environ["DB_PORT"].strip()

# Browserless
BROWSERLESS_CLIENT_ID = os.environ["BROWSERLESS_CLIENT_ID"].strip()
BROWSERLESS_CLIENT_SECRET = os.environ["BROWSERLESS_CLIENT_SECRET"].strip()

# SD
SD_USERNAME = os.environ["SD_USERNAME"].strip()
SD_PASSWORD = os.environ["SD_PASSWORD"].strip()
SD_URL = os.environ["SD_URL"].strip()

# SD personalesag robot
SD_PERSONALESAG_ROBOT_USERNAME = os.environ["SD_PERSONALESAG_ROBOT_USERNAME"].strip()
SD_PERSONALESAG_ROBOT_PASSWORD = os.environ["SD_PERSONALESAG_ROBOT_PASSWORD"].strip()