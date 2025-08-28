import os
import uuid
from typing import Optional
from supabase import Client
from whatsapp_agent.database.base import DataBase
from whatsapp_agent._debug import Logger


class SupabaseStorageManager(DataBase):
    def __init__(self):
        super().__init__()
        self.bucket_name = "whatsapp-files"  # Default bucket name
        # Ensure the bucket exists
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Ensure the Supabase storage bucket exists"""
        try:
            # Try to get the bucket
            bucket_info = self.supabase.storage.get_bucket(self.bucket_name)
            Logger.info(f"✅ Supabase storage bucket '{self.bucket_name}' exists")
        except Exception as e:
            # If bucket doesn't exist, create it
            Logger.info(f"Creating Supabase storage bucket '{self.bucket_name}'")
            try:
                self.supabase.storage.create_bucket(self.bucket_name)
                Logger.info(f"✅ Created Supabase storage bucket '{self.bucket_name}'")
            except Exception as create_error:
                Logger.error(f"❌ Failed to create Supabase storage bucket '{self.bucket_name}': {create_error}")

    def upload_file(self, file_path: str, file_name: Optional[str] = None, content_type: Optional[str] = None) -> Optional[str]:
        """
        Upload a file to Supabase storage.
        
        Args:
            file_path: Path to the file to upload
            file_name: Optional custom file name (if None, a UUID will be generated)
            content_type: Optional content type for the file
            
        Returns:
            URL of the uploaded file or None if upload failed
        """
        try:
            # Generate a unique file name if not provided
            if not file_name:
                file_extension = os.path.splitext(file_path)[1]
                file_name = f"{uuid.uuid4()}{file_extension}"
            
            # Upload file to Supabase storage
            with open(file_path, 'rb') as f:
                # Prepare file options
                file_options = {}
                if content_type:
                    file_options["content-type"] = content_type
                
                # Upload the file
                response = self.supabase.storage.from_(self.bucket_name).upload(
                    file_name, 
                    f, 
                    file_options
                )
                
                if response:
                    # Get the public URL of the uploaded file
                    public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(file_name)
                    Logger.info(f"✅ File uploaded successfully: {public_url}")
                    return public_url
                else:
                    Logger.error("❌ Failed to upload file to Supabase storage")
                    return None
                    
        except Exception as e:
            Logger.error(f"❌ Error uploading file to Supabase storage: {e}")
            return None
    
    def delete_file(self, file_name: str) -> bool:
        """
        Delete a file from Supabase storage.
        
        Args:
            file_name: Name of the file to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            response = self.supabase.storage.from_(self.bucket_name).remove([file_name])
            if response:
                Logger.info(f"✅ File deleted successfully: {file_name}")
                return True
            else:
                Logger.error(f"❌ Failed to delete file: {file_name}")
                return False
        except Exception as e:
            Logger.error(f"❌ Error deleting file from Supabase storage: {e}")
            return False
    
    def get_file_url(self, file_name: str) -> Optional[str]:
        """
        Get the public URL of a file in Supabase storage.
        
        Args:
            file_name: Name of the file
            
        Returns:
            Public URL of the file or None if error
        """
        try:
            public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(file_name)
            return public_url
        except Exception as e:
            Logger.error(f"❌ Error getting file URL from Supabase storage: {e}")
            return None