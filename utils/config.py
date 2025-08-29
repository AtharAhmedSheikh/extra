import os
from dotenv import load_dotenv
from whatsapp_agent._debug import Logger

load_dotenv()

class Config:
    """Manages application configuration"""
    
    _supabase_url = os.environ.get("SUPABASE_URL")
    _supabase_service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    _credentials_manager = None
    _version = 0
    _listeners = set()
    
    @classmethod
    def _get_credentials_manager(cls):
        """Get or create the credentials manager instance"""
        if cls._credentials_manager is None:
            from whatsapp_agent.database.credentials import CredentialsManager
            cls._credentials_manager = CredentialsManager()
        return cls._credentials_manager
    
    @classmethod
    def get_whatsapp_headers(cls):
        """Get WhatsApp API headers"""
        credentials_manager = cls._get_credentials_manager()
        access_token = credentials_manager.get_credential("WHATSAPP_ACCESS_TOKEN")
        Logger.info("Using WhatsApp access token for headers (dynamic fetch)")
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        

    @classmethod
    def get(cls, key, default=None):
        """Get a configuration value"""
        if key == "SUPABASE_URL":
            return cls._supabase_url
        elif key == "SUPABASE_SERVICE_ROLE_KEY":
            return cls._supabase_service_role_key
        
        # For all other credentials, use the credentials manager
        credentials_manager = cls._get_credentials_manager()
        value = credentials_manager.get_credential(key, default)
        Logger.info(f"Fetched credential '{key}' (dynamic)")
        return value
    
    @classmethod
    def set(cls, key, value):
        """Set a configuration value and update it in the database"""
        if key == "SUPABASE_URL" or key == "SUPABASE_SERVICE_ROLE_KEY":
            raise ValueError(f"Cannot set {key} - Read Only environment variable")
        
        # For all other credentials, use the credentials manager
        credentials_manager = cls._get_credentials_manager()
        updated = credentials_manager.set_credential(key, value)
        if updated:
            Logger.info(f"Updated credential '{key}' and invalidated cache")
            cls._bump_version_and_notify()

    @classmethod
    def reload(cls):
        """Force reload all credentials and notify listeners."""
        credentials_manager = cls._get_credentials_manager()
        credentials_manager.reload_credentials()
        Logger.info("Reloaded credentials from store and invalidated cache")
        cls._bump_version_and_notify()

    @classmethod
    def get_version(cls):
        """Return monotonically increasing version to detect config changes."""
        return cls._version

    @classmethod
    def add_listener(cls, callback):
        """Register a callback to be invoked on config changes."""
        if callable(callback):
            cls._listeners.add(callback)

    @classmethod
    def remove_listener(cls, callback):
        """Unregister a previously registered callback."""
        if callback in cls._listeners:
            cls._listeners.remove(callback)

    @classmethod
    def _bump_version_and_notify(cls):
        cls._version += 1
        Logger.info(f"Config version bumped to {cls._version}; notifying listeners")
        for callback in list(cls._listeners):
            try:
                callback(cls._version)
            except Exception:
                # Best effort; don't break on listener errors
                pass