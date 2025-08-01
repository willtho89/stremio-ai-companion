"""
Tests for the encryption service.
"""

import pytest
import json
from fastapi import HTTPException
from app.services.encryption import EncryptionService
from app.models.config import Config


class TestEncryptionService:
    """Tests for the EncryptionService class."""

    def test_encrypt_decrypt(self):
        """Test that encryption and decryption work correctly."""
        service = EncryptionService(password="test-password")
        original_data = "This is a test string"
        
        encrypted = service.encrypt(original_data)
        decrypted = service.decrypt(encrypted)
        
        assert decrypted == original_data
        assert encrypted != original_data  # Ensure it was actually encrypted

    def test_encrypt_decrypt_with_json(self):
        """Test encryption and decryption with JSON data."""
        service = EncryptionService(password="test-password")
        config = Config(
            openai_api_key="sk-test123456789012345678901234567890",
            tmdb_read_access_token="eyJhbGciOiJIUzI1NiJ9.test1234567890"
        )
        
        original_data = config.model_dump_json()
        
        encrypted = service.encrypt(original_data)
        decrypted = service.decrypt(encrypted)
        
        # Verify we can parse the decrypted JSON back into a Config object
        decrypted_config = Config.model_validate(json.loads(decrypted))
        
        assert decrypted == original_data
        assert decrypted_config.openai_api_key == config.openai_api_key
        assert decrypted_config.tmdb_read_access_token == config.tmdb_read_access_token

    def test_decrypt_with_wrong_password(self):
        """Test decryption with the wrong password."""
        service1 = EncryptionService(password="password1")
        service2 = EncryptionService(password="password2")
        
        original_data = "This is a test string"
        encrypted = service1.encrypt(original_data)
        
        with pytest.raises(HTTPException) as exc_info:
            service2.decrypt(encrypted)
        
        assert exc_info.value.status_code == 400
        assert "Invalid config data" in exc_info.value.detail

    def test_decrypt_with_invalid_data(self):
        """Test decryption with invalid data."""
        service = EncryptionService(password="test-password")
        
        with pytest.raises(HTTPException) as exc_info:
            service.decrypt("not-valid-base64!")
        
        assert exc_info.value.status_code == 400
        assert "Invalid config data" in exc_info.value.detail

    def test_different_instances_same_password(self):
        """Test that different instances with the same password can decrypt each other's data."""
        service1 = EncryptionService(password="same-password")
        service2 = EncryptionService(password="same-password")
        
        original_data = "This is a test string"
        encrypted = service1.encrypt(original_data)
        decrypted = service2.decrypt(encrypted)
        
        assert decrypted == original_data

    def test_encryption_is_not_deterministic(self):
        """Test that encryption is not deterministic (same input gives different output)."""
        service = EncryptionService(password="test-password")
        original_data = "This is a test string"
        
        encrypted1 = service.encrypt(original_data)
        encrypted2 = service.encrypt(original_data)
        
        assert encrypted1 != encrypted2  # Different salt should result in different output
        
        # But both should decrypt to the same original data
        assert service.decrypt(encrypted1) == original_data
        assert service.decrypt(encrypted2) == original_data