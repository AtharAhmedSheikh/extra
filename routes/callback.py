from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from intuitlib.client import AuthClient

from whatsapp_agent._debug import Logger
from whatsapp_agent.utils.config import Config


# Create FastAPI router
callback = APIRouter(tags=["Callback"])

def save_token(auth_client, realm_id, auth_code):
    Config.set("QB_ACCESS_TOKEN", auth_client.access_token)
    Config.set("QB_REFRESH_TOKEN", auth_client.refresh_token)
    Config.set("QB_REALM_ID", realm_id)
    Config.set("QB_AUTH_CODE", auth_code)

def _build_auth_client():
    return AuthClient(
        client_id=Config.get("QB_CLIENT_ID"),
        client_secret=Config.get("QB_CLIENT_SECRET"),
        environment=Config.get("QB_ENVIRONMENT"),
        redirect_uri=Config.get("QB_REDIRECT_URI")
    )

@callback.post("/callback")
async def func(request: Request):
    try:
        # For POST requests, parse the JSON
        data = await request.json()
        Logger.info(f"POST Callback Data (not usually used in Intuit OAuth): {data}")
        return PlainTextResponse("POST callback received")
    except Exception as e:
        Logger.error(f"{__name__}: /callback -> Error processing POST callback: {e}")
        return PlainTextResponse("Error", status_code=500)

@callback.get("/callback")
async def oauth_callback(request: Request):
    try:
        # Extract query parameters from redirect URL
        query_params = dict(request.query_params)
        Logger.info(f"GET Callback Query Params: {query_params}")

        auth_code = query_params.get("code")
        realm_id = query_params.get("realmId")

        if not auth_code or not realm_id:
            return PlainTextResponse("Missing code or realmId", status_code=400)

        # Exchange auth code for tokens
        auth_client = _build_auth_client()
        auth_client.get_bearer_token(auth_code, realm_id=realm_id)
        Logger.info(f"Access Token: {auth_client.access_token}")
        Logger.info(f"Refresh Token: {auth_client.refresh_token}")

        save_token(auth_client, realm_id, auth_code)

        return PlainTextResponse("OAuth success! Tokens received. Check your logs.")
    except Exception as e:
        Logger.error(f"{__name__}: /callback -> Error during OAuth callback processing: {e}")
        return PlainTextResponse("Error during OAuth callback", status_code=500)
