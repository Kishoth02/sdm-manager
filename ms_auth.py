import os
import msal
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")
REDIRECT_URI = os.getenv("REDIRECT_URI")
TENANT_SUBDOMAIN = os.getenv("TENANT_SUBDOMAIN")
AUTHORITY = f"https://{TENANT_SUBDOMAIN}.ciamlogin.com/{TENANT_ID}"
SCOPE = ["User.Read"]

def get_msal_app():
    return msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
    )

def get_auth_url():
    return get_msal_app().get_authorization_request_url(
        SCOPE,
        redirect_uri=REDIRECT_URI,
    )

def get_token_from_code(code):
    return get_msal_app().acquire_token_by_authorization_code(
        code,
        scopes=SCOPE,
        redirect_uri=REDIRECT_URI,
    )