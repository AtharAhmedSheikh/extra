from intuitlib.client import AuthClient
from intuitlib.enums import Scopes
from typing import Dict, Any, Optional
from whatsapp_agent._debug import Logger
from whatsapp_agent.utils.config import Config

import time
import webbrowser
import requests
import asyncio


class QuickBookBase:
    BASE_URL = "https://quickbooks.api.intuit.com/v3/company"
    API_VERSION = "70"

    def __init__(self):
        self._config_version = Config.get_version()
        self.auth_client = self._create_client()
        self.tokens = self._load_tokens()
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.get_access_token()}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        })
        Config.add_listener(self._on_config_change)

    def _on_config_change(self, new_version: int):
        try:
            self._config_version = new_version
            # Recreate client and refresh session headers based on latest tokens
            Logger.info("Config changed: reinitializing QuickBooks client, tokens and session headers")
            self.auth_client = self._create_client()
            self.tokens = self._load_tokens()
            self.session.headers.update({
                "Authorization": f"Bearer {self.get_access_token()}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            })
        except Exception:
            pass

    def _create_client(self):
        return AuthClient(
            client_id=Config.get("QB_CLIENT_ID"),
            client_secret=Config.get("QB_CLIENT_SECRET"),
            redirect_uri=Config.get("QB_REDIRECT_URI"),
            environment=Config.get("QB_ENVIRONMENT"),
        )

    def _load_tokens(self):
        return {
            "access_token": Config.get("QB_ACCESS_TOKEN"),
            "refresh_token": Config.get("QB_REFRESH_TOKEN"),
            "realm_id": Config.get("QB_REALM_ID"),
            "access_token_created_at": float(Config.get("QB_ACCESS_TOKEN_CREATED_AT"))
        }

    def _save_tokens(self):
        Config.set("QB_ACCESS_TOKEN", self.tokens["access_token"])
        Config.set("QB_REFRESH_TOKEN", self.tokens["refresh_token"])
        Config.set("QB_REALM_ID", self.tokens["realm_id"])
        Config.set("QB_ACCESS_TOKEN_CREATED_AT", str(self.tokens["access_token_created_at"]))

    async def _authentication_flow(self):
        Logger.warning("\n[🔐] No valid tokens found. Starting new authentication flow...")
        auth_url = self.auth_client.get_authorization_url([Scopes.ACCOUNTING])
        Logger.info(f"Please open this URL and authorize the app:\n{auth_url}")
        webbrowser.open(auth_url)

        Logger.info("[⏳] Waiting for callback data to be stored...")
        await asyncio.sleep(20)  # Non-blocking wait

        # Fetch from env (set by your callback endpoint)
        auth_code = Config.get("QB_AUTH_CODE")
        realm_id = Config.get("QB_REALM_ID")

        if not auth_code or not realm_id:
            raise RuntimeError("[❌] Auth code or Realm ID not found after waiting.")

        # Exchange code for tokens
        self.auth_client.get_bearer_token(auth_code, realm_id)

        self.tokens = {
            "access_token": self.auth_client.access_token,
            "refresh_token": self.auth_client.refresh_token,
            "realm_id": realm_id,
            "access_token_created_at": time.time()
        }
        self._save_tokens()
        Logger.info("[✅] Tokens saved successfully!")
        return self.tokens["access_token"]

    def _is_access_token_expired(self):
        created_at = self.tokens.get("access_token_created_at")
        return not created_at or (time.time() - created_at) > 3500

    def _test_access_token(self):
        access_token = self.tokens.get("access_token")
        realm_id = self.tokens.get("realm_id")
        if not access_token or not realm_id:
            return False

        url = f"{self.BASE_URL}/{realm_id}/companyinfo/{realm_id}"
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        res = requests.get(url, headers=headers)
        return res.status_code != 401

    def _refresh_access_token(self):
        try:
            self.auth_client.refresh(self.tokens["refresh_token"])
            self.tokens["access_token"] = self.auth_client.access_token
            self.tokens["refresh_token"] = self.auth_client.refresh_token
            self.tokens["access_token_created_at"] = time.time()
            self._save_tokens()
            Logger.info("[✅] Access token refreshed successfully.")
            return self.tokens["access_token"]
        except Exception as e:
            Logger.error(f"{__name__}: _refresh_access_token -> [❌] Refresh token invalid: {e}")
            return None

    def _get_url(self, endpoint: str) -> str:
        return f"{self.BASE_URL}/{self.get_realm_id()}/{endpoint}"

    def _request(self, method: str, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        try:
            response = self.session.request(method, url, **kwargs)
            if response.ok:
                return response.json()
            Logger.error(f"{__name__}: _request -> [❌] API Error: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            Logger.error(f"{__name__}: _request -> [❌] Request failed: {e}")
        return None

    def get_access_token(self):
        if not self.tokens.get("access_token"):
            return self._run_auth_flow()

        if self._is_access_token_expired() or not self._test_access_token():
            Logger.info("[ℹ️] Access token expired or invalid. Trying refresh...")
            new_token = self._refresh_access_token()
            if new_token:
                return new_token
            else:
                Logger.warning("[⚠️] Refresh failed. Starting new auth flow...")
                return self._run_auth_flow()

        return self.tokens.get("access_token")

    def _run_auth_flow(self):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No loop running → safe to use asyncio.run
            return asyncio.run(self._authentication_flow())
        else:
            # Loop running → must schedule coroutine
            future = asyncio.ensure_future(self._authentication_flow())
            # WARNING: This will block until done, but won't break the loop
            return loop.run_until_complete(future)


    def get_realm_id(self):
        return self.tokens.get("realm_id")
