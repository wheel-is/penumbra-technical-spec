"""Contract tests for ESPN Provider."""

import pytest
import httpx
from unittest.mock import AsyncMock, patch
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from espn_provider.provider import ESPNProvider
from espn_provider.router import router


@pytest.fixture
def espn_provider():
    """Create ESPN provider instance."""
    provider = ESPNProvider()
    return provider


@pytest.fixture
def mock_client():
    """Create mock HTTP client."""
    mock = AsyncMock(spec=httpx.AsyncClient)
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)
    return mock


@pytest.mark.asyncio
@pytest.mark.contract
async def test_provider_initialization(espn_provider):
    """Test that provider initializes correctly."""
    assert espn_provider is not None
    assert espn_provider.manifest_path.name == "provider.yaml"
    assert espn_provider.router is not None
    
    # Test startup and shutdown
    await espn_provider.startup()
    await espn_provider.shutdown()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_get_home_feed(mock_client):
    """Test home feed endpoint."""
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "content": [{"id": "1", "type": "news"}]
    }
    mock_response.status_code = 200
    mock_response.raise_for_status = AsyncMock()
    
    mock_client.get.return_value = mock_response
    
    with patch('espn_provider.router.httpx.AsyncClient') as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client
        from espn_provider.router import get_home_feed
        result = await get_home_feed(lang="en", region="US", platform="ios", personalized=True, limit=20)
        
        assert result is not None
        assert "clubhouse" in result or "feed" in result


@pytest.mark.asyncio
@pytest.mark.contract 
async def test_get_scores(mock_client):
    """Test scores endpoint."""
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "content": [{"sportName": "NFL", "events": []}]
    }
    mock_response.status_code = 200
    mock_response.raise_for_status = AsyncMock()
    
    mock_client.get.return_value = mock_response
    
    with patch('espn_provider.router.httpx.AsyncClient') as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client
        from espn_provider.router import get_scores
        result = await get_scores(lang="en", region="US", sport="nfl")
        
        assert result is not None
        assert isinstance(result, dict)


@pytest.mark.asyncio
@pytest.mark.contract
async def test_get_sports_list(mock_client):
    """Test sports list endpoint."""
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "sports": [
            {"id": "nfl", "name": "NFL"},
            {"id": "nba", "name": "NBA"}
        ]
    }
    mock_response.status_code = 200
    mock_response.raise_for_status = AsyncMock()
    
    mock_client.get.return_value = mock_response
    
    with patch('espn_provider.router.httpx.AsyncClient') as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client
        from espn_provider.router import get_sports_list
        result = await get_sports_list(profile="sports-card", lang="en", region="US")
        
        assert result is not None
        assert hasattr(result, 'sports')


@pytest.mark.asyncio
@pytest.mark.contract
async def test_search_content(mock_client):
    """Test search endpoint."""
    from espn_provider.router import search_content
    result = await search_content(query="Lakers", type="teams", limit=10)
    
    assert result is not None
    assert "query" in result
    assert result["query"] == "Lakers"


@pytest.mark.asyncio
@pytest.mark.contract
async def test_error_handling(espn_provider):
    """Test error handling."""
    from fastapi import HTTPException
    
    # Test HTTP exception handling
    error = HTTPException(status_code=404, detail="Not found")
    result = espn_provider.handle_error(error)
    
    assert "error" in result
    assert result["error"]["provider_id"] == "espn"
    assert result["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert result["error"]["status"] == 404
    
    # Test generic exception handling
    error = Exception("Something went wrong")
    result = espn_provider.handle_error(error)
    
    assert "error" in result
    assert result["error"]["provider_id"] == "espn"
    assert result["error"]["code"] == "INTERNAL_ERROR"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-m", "contract"])
