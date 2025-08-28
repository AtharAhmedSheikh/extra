import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Manages application configuration"""
    
    _supabase_url = os.environ.get("SUPABASE_URL")
    _supabase_service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    _credentials_manager = None
    
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
        return credentials_manager.get_credential(key, default)
    
    @classmethod
    def set(cls, key, value):
        """Set a configuration value and update it in the database"""
        if key == "SUPABASE_URL" or key == "SUPABASE_SERVICE_ROLE_KEY":
            raise ValueError(f"Cannot set {key} - Read Only environment variable")
        
        # For all other credentials, use the credentials manager
        credentials_manager = cls._get_credentials_manager()
        credentials_manager.set_credential(key, value)