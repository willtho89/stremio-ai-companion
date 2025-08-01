"""
Encryption service for the Stremio AI Companion application.
"""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from fastapi import HTTPException

from app.core.logging import logger
from app.core.config import settings

class EncryptionService:
    """
    Service for encrypting and decrypting configuration data.
    
    This service uses Fernet symmetric encryption with a key derived
    from a password using PBKDF2.
    """
    
    def __init__(self, password: str = None):
        """
        Initialize the encryption service with a password.
        
        Args:
            password: The password to use for encryption/decryption.
                     If not provided, uses the value from settings.
        """
        self.password = (password or settings.ENCRYPTION_KEY).encode()
        
    def _get_key(self, salt: bytes) -> bytes:
        """
        Derive a key from the password and salt using PBKDF2.
        
        Args:
            salt: Random salt for key derivation
            
        Returns:
            Base64-encoded key for Fernet
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(self.password))
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt data using Fernet symmetric encryption.
        
        Args:
            data: The string data to encrypt
            
        Returns:
            Base64-encoded encrypted data with salt
        """
        salt = os.urandom(16)
        key = self._get_key(salt)
        f = Fernet(key)
        encrypted = f.encrypt(data.encode())
        return base64.urlsafe_b64encode(salt + encrypted).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt data that was encrypted with this service.
        
        Args:
            encrypted_data: Base64-encoded encrypted data with salt
            
        Returns:
            The decrypted string data
            
        Raises:
            HTTPException: If decryption fails
        """
        try:
            data = base64.urlsafe_b64decode(encrypted_data.encode())
            salt = data[:16]
            encrypted = data[16:]
            key = self._get_key(salt)
            f = Fernet(key)
            return f.decrypt(encrypted).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt config data: {e}")
            raise HTTPException(status_code=400, detail="Invalid config data")

# Create a singleton instance
encryption_service = EncryptionService()