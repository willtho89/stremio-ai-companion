"""
Test script to verify that the application correctly handles URL schemes when behind a proxy.

This script simulates a request with the X-Forwarded-Proto header set to "https"
and checks if the manifest URL in the response uses HTTPS.
"""

import requests
import json
import sys

# Base URL of the application
BASE_URL = "http://localhost:8000"


def test_scheme_handling():
    """Test that the application correctly handles URL schemes when behind a proxy."""
    print("Testing URL scheme handling...")

    # Test the save-config endpoint with X-Forwarded-Proto header
    headers = {"X-Forwarded-Proto": "https", "Content-Type": "application/x-www-form-urlencoded"}

    # Minimal form data required for the save-config endpoint
    data = {
        "openai_api_key": "test_key",
        "tmdb_read_access_token": "test_token",
        "model_name": "test_model",
        "max_results": 10,
    }

    try:
        response = requests.post(f"{BASE_URL}/save-config", headers=headers, data=data)
        response.raise_for_status()

        # Parse the response JSON
        result = response.json()

        # Check if the manifest URL uses HTTPS
        if "manifest_url" in result and result["manifest_url"].startswith("https://"):
            print("✅ Success: Manifest URL uses HTTPS scheme")
            print(f"Manifest URL: {result['manifest_url']}")
            return True
        else:
            print("❌ Error: Manifest URL does not use HTTPS scheme")
            print(f"Response: {json.dumps(result, indent=2)}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Error making request: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = test_scheme_handling()
    sys.exit(0 if success else 1)
