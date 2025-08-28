import os
import base64
from cryptography.fernet import Fernet
from whatsapp_agent.database.base import DataBase


class SecretsMigration(DataBase):
    """Migration script to encrypt existing plain text secrets"""
    
    def __init__(self):
        super().__init__()
        self._encryption_key = self._get_encryption_key()
    
    def _get_encryption_key(self):
        """Get encryption key from environment variable"""
        key = os.getenv('ENCRYPTION_KEY')
        if not key:
            raise ValueError("CREDENTIALS_ENCRYPTION_KEY environment variable not set")
        
        # If the key is not in the correct format, generate it from the provided string
        try:
            # Try to use it directly (if it's already a Fernet key)
            Fernet(key.encode())
            return key.encode()
        except:
            # Generate a Fernet key from the provided string
            key_bytes = key.encode('utf-8')
            # Pad or truncate to 32 bytes for Fernet
            key_bytes = key_bytes[:32].ljust(32, b'0')
            return base64.urlsafe_b64encode(key_bytes)
    
    def _encrypt_value(self, value: str) -> str:
        """Encrypt a credential value"""
        fernet = Fernet(self._encryption_key)
        encrypted_bytes = fernet.encrypt(value.encode('utf-8'))
        return base64.b64encode(encrypted_bytes).decode('utf-8')
    
    def _is_encrypted(self, value: str) -> bool:
        """Check if a value is already encrypted by trying to decrypt it"""
        try:
            fernet = Fernet(self._encryption_key)
            # Try to decode base64 first
            encrypted_bytes = base64.b64decode(value.encode('utf-8'))
            # Try to decrypt
            fernet.decrypt(encrypted_bytes)
            return True
        except:
            return False
    
    def migrate_secrets(self, dry_run=True):
        """
        Migrate all plain text secrets to encrypted format
        
        Args:
            dry_run (bool): If True, only shows what would be updated without making changes
        """
        print("Starting secrets migration...")
        print(f"Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
        print("-" * 50)
        
        try:
            # Fetch all existing secrets
            response = self.supabase.table("secrets").select("credname, value").execute()
            
            if not response.data:
                print("No secrets found in database.")
                return
            
            secrets_to_update = []
            already_encrypted = []
            
            # Check each secret
            for item in response.data:
                credname = item["credname"]
                value = item["value"]
                
                if self._is_encrypted(value):
                    already_encrypted.append(credname)
                    print(f"✓ {credname}: Already encrypted")
                else:
                    secrets_to_update.append(item)
                    print(f"→ {credname}: Needs encryption")
            
            print(f"\nSummary:")
            print(f"- Already encrypted: {len(already_encrypted)}")
            print(f"- Need encryption: {len(secrets_to_update)}")
            
            if not secrets_to_update:
                print("\nNo secrets need to be encrypted. Migration complete!")
                return
            
            if dry_run:
                print(f"\nDRY RUN: Would encrypt {len(secrets_to_update)} secrets")
                print("Run with dry_run=False to perform actual migration")
                return
            
            # Perform actual encryption and updates
            print(f"\nEncrypting and updating {len(secrets_to_update)} secrets...")
            
            updated_count = 0
            failed_updates = []
            
            for item in secrets_to_update:
                credname = item["credname"]
                plain_value = item["value"]
                
                try:
                    # Encrypt the value
                    encrypted_value = self._encrypt_value(plain_value)
                    
                    # Update in database
                    update_response = self.supabase.table("secrets").update({
                        "value": encrypted_value
                    }).eq("credname", credname).execute()
                    
                    if update_response.data:
                        print(f"✓ Updated: {credname}")
                        updated_count += 1
                    else:
                        print(f"✗ Failed to update: {credname}")
                        failed_updates.append(credname)
                        
                except Exception as e:
                    print(f"✗ Error updating {credname}: {e}")
                    failed_updates.append(credname)
            
            print(f"\nMigration Results:")
            print(f"- Successfully updated: {updated_count}")
            print(f"- Failed updates: {len(failed_updates)}")
            
            if failed_updates:
                print(f"- Failed credentials: {', '.join(failed_updates)}")
            
            if updated_count > 0:
                print(f"\n✅ Migration completed! {updated_count} secrets are now encrypted.")
            
        except Exception as e:
            print(f"Error during migration: {e}")
    
    def verify_migration(self):
        """Verify that all secrets can be properly decrypted"""
        print("Verifying migration...")
        print("-" * 30)
        
        try:
            response = self.supabase.table("secrets").select("credname, value").execute()
            
            if not response.data:
                print("No secrets found in database.")
                return
            
            fernet = Fernet(self._encryption_key)
            success_count = 0
            failed_decryptions = []
            
            for item in response.data:
                credname = item["credname"]
                encrypted_value = item["value"]
                
                try:
                    # Try to decrypt
                    encrypted_bytes = base64.b64decode(encrypted_value.encode('utf-8'))
                    decrypted_bytes = fernet.decrypt(encrypted_bytes)
                    decrypted_value = decrypted_bytes.decode('utf-8')
                    
                    print(f"✓ {credname}: Successfully decrypted")
                    success_count += 1
                    
                except Exception as e:
                    print(f"✗ {credname}: Failed to decrypt - {e}")
                    failed_decryptions.append(credname)
            
            print(f"\nVerification Results:")
            print(f"- Successfully decrypted: {success_count}")
            print(f"- Failed decryptions: {len(failed_decryptions)}")
            
            if failed_decryptions:
                print(f"- Failed credentials: {', '.join(failed_decryptions)}")
            
            if len(failed_decryptions) == 0:
                print("✅ All secrets can be properly decrypted!")
            
        except Exception as e:
            print(f"Error during verification: {e}")


def main():
    """Main migration function"""
    print("🔐 Secrets Encryption Migration Tool")
    print("=" * 40)
    
    # Check if encryption key is set
    if not os.getenv('ENCRYPTION_KEY'):
        print("❌ Error: CREDENTIALS_ENCRYPTION_KEY environment variable not set")
        print("Please set your encryption key and try again.")
        return
    
    try:
        migration = SecretsMigration()
        
        print("1. Running dry run to check current state...")
        migration.migrate_secrets(dry_run=True)
        
        print("\n" + "=" * 50)
        user_input = input("\nProceed with actual migration? (yes/no): ").lower().strip()
        
        if user_input in ['yes', 'y']:
            print("\n2. Running actual migration...")
            migration.migrate_secrets(dry_run=False)
            
            print("\n3. Verifying migration...")
            migration.verify_migration()
        else:
            print("Migration cancelled by user.")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")


if __name__ == "__main__":
    main()