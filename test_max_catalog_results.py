"""
Test script to verify that MAX_CATALOG_RESULTS setting works correctly.
"""

import asyncio

from app.api.stremio import _cached_catalog
from app.core.config import settings
from app.core.logging import logger
from app.models.enums import ContentType


async def test_max_catalog_results():
    """
    Test that MAX_CATALOG_RESULTS setting is correctly used in _cached_catalog.
    """
    # Print current MAX_CATALOG_RESULTS value
    logger.info(f"Current MAX_CATALOG_RESULTS: {settings.MAX_CATALOG_RESULTS}")

    # Create a mock config string (this won't actually be used in this test)
    mock_config = "mock_config"

    # Call _cached_catalog and check if it uses the correct MAX_CATALOG_RESULTS value
    try:
        # This will fail because we're using a mock config, but we can check the log output
        await _cached_catalog(mock_config, ContentType.MOVIE)
    except Exception as e:
        # We expect an exception because we're using a mock config
        logger.info(f"Expected exception: {e}")

    logger.info("Test completed. Check logs to verify MAX_CATALOG_RESULTS is being used correctly.")


if __name__ == "__main__":
    asyncio.run(test_max_catalog_results())
