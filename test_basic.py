import pytest
import httpx
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_homepage():
    """Test that the homepage loads successfully"""
    response = client.get("/")
    assert response.status_code == 200
    assert "let's stream vibes" in response.text

def test_configure_page():
    """Test that the configure page loads successfully"""
    response = client.get("/configure")
    assert response.status_code == 200
    assert "Configure AI Search" in response.text

def test_manifest_without_config():
    """Test that manifest endpoint requires config parameter"""
    response = client.get("/manifest.json")
    assert response.status_code == 422  # Validation error for missing config

def test_catalog_without_config():
    """Test that catalog endpoint requires config parameter"""
    response = client.get("/catalog/movie/test.json")
    assert response.status_code == 422  # Validation error for missing config

def test_save_config_validation():
    """Test config validation with invalid data"""
    response = client.post("/save-config", data={
        "openai_api_key": "short",  # Too short
        "tmdb_api_key": "short",    # Too short
        "max_results": 100          # Too high
    })
    assert response.status_code == 400
    data = response.json()
    assert not data["success"]
    assert "Validation failed" in data["detail"]

def test_encryption_service():
    """Test encryption and decryption"""
    from main import EncryptionService
    
    service = EncryptionService("test-key")
    original = "test data"
    encrypted = service.encrypt(original)
    decrypted = service.decrypt(encrypted)
    
    assert decrypted == original
    assert encrypted != original

def test_reconfigure_functionality():
    """Test the configure endpoint with existing config and form handling"""
    from main import encryption_service, Config
    import json
    
    # Create a test config
    config = Config(
        openai_api_key="test-openai-key",
        tmdb_api_key="test-tmdb-key",
        max_results=25,
        use_posterdb=True,
        posterdb_api_key="test-posterdb-key"
    )
    
    # Encrypt it
    encrypted = encryption_service.encrypt(config.model_dump_json())
    
    # Test configure page loads with existing config
    response = client.get(f"/configure?config={encrypted}")
    assert response.status_code == 200
    assert "Reconfigure AI Search" in response.text
    assert "test-openai-key" in response.text
    
    # Test saving updated config (checkbox unchecked)
    response = client.post("/save-config", data={
        "openai_api_key": "updated-key",
        "tmdb_api_key": "updated-tmdb",
        "max_results": "30",
        # use_posterdb not included (unchecked)
        "posterdb_api_key": ""
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    # Verify the new config
    new_config_param = data["manifest_url"].split("config=")[1]
    decrypted = encryption_service.decrypt(new_config_param)
    new_config = json.loads(decrypted)
    assert new_config["max_results"] == 30
    assert new_config["use_posterdb"] is False
    
    # Test saving with RPDB enabled
    response = client.post("/save-config", data={
        "openai_api_key": "updated-key",
        "tmdb_api_key": "updated-tmdb",
        "max_results": "25",
        "use_posterdb": "on",  # RPDB enabled
        "posterdb_api_key": "test-rpdb-key"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    # Verify RPDB config
    new_config_param = data["manifest_url"].split("config=")[1]
    decrypted = encryption_service.decrypt(new_config_param)
    new_config = json.loads(decrypted)
    assert new_config["use_posterdb"] is True
    assert new_config["posterdb_api_key"] == "test-rpdb-key"

if __name__ == "__main__":
    pytest.main([__file__])