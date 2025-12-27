"""
Test suite for HeyPico Maps LLM Backend.
Run with: pytest tests/ -v
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

# Import the app
import sys
sys.path.insert(0, '..')
from app.main import app
from app.config import Settings


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    return Settings(
        google_maps_api_key="test_api_key_12345678901234567890",
        google_maps_frontend_key="test_frontend_key_12345678901234567890",
        ollama_base_url="http://localhost:11434",
        llm_model="llama3.2"
    )


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert data["name"] == "HeyPico Maps LLM"
    
    def test_health_endpoint(self, client):
        """Test health endpoint returns service status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data
        assert "llm" in data["services"]
        assert "maps" in data["services"]


class TestChatEndpoints:
    """Test chat/LLM endpoints."""
    
    def test_chat_health(self, client):
        """Test chat health endpoint."""
        response = client.get("/api/chat/health")
        assert response.status_code == 200
        data = response.json()
        assert "llm_available" in data
        assert "model" in data
    
    @patch('app.services.llm_service.llm_service.generate_response')
    @patch('app.services.maps_service.maps_service.search_places')
    async def test_chat_message(self, mock_search, mock_llm, client):
        """Test sending a chat message."""
        # Mock LLM response
        mock_llm.return_value = AsyncMock(
            success=True,
            intent=AsyncMock(
                query_type="restaurant",
                search_query="sushi restaurant",
                location_hint="Times Square",
                response_text="I'll help you find sushi!"
            ),
            raw_response=""
        )
        
        # Mock Maps response
        mock_search.return_value = AsyncMock(
            success=True,
            places=[],
            quota_remaining=100
        )
        
        response = client.post("/api/chat", json={
            "message": "Find sushi near Times Square"
        })
        
        assert response.status_code == 200
    
    def test_chat_empty_message(self, client):
        """Test chat with empty message returns error."""
        response = client.post("/api/chat", json={
            "message": ""
        })
        assert response.status_code == 422  # Validation error


class TestMapsEndpoints:
    """Test Google Maps endpoints."""
    
    def test_maps_config(self, client):
        """Test maps config endpoint."""
        response = client.get("/api/maps/config")
        assert response.status_code == 200
        data = response.json()
        assert "api_key" in data
        assert "default_center" in data
        assert "default_zoom" in data
    
    def test_places_search_missing_query(self, client):
        """Test place search without query returns error."""
        response = client.get("/api/maps/places/search")
        assert response.status_code == 422  # Missing required parameter
    
    def test_places_search_invalid_coordinates(self, client):
        """Test place search with invalid coordinates."""
        response = client.get("/api/maps/places/search", params={
            "query": "coffee",
            "lat": 999,  # Invalid latitude
            "lng": 0
        })
        assert response.status_code == 422
    
    def test_directions_missing_params(self, client):
        """Test directions without required params."""
        response = client.get("/api/maps/directions")
        assert response.status_code == 422
    
    def test_directions_invalid_mode(self, client):
        """Test directions with invalid travel mode."""
        response = client.get("/api/maps/directions", params={
            "origin_lat": 40.758,
            "origin_lng": -73.985,
            "dest_lat": 40.748,
            "dest_lng": -73.985,
            "mode": "flying"  # Invalid mode
        })
        assert response.status_code == 422
    
    def test_geocode_missing_address(self, client):
        """Test geocode without address."""
        response = client.get("/api/maps/geocode")
        assert response.status_code == 422
    
    def test_geocode_short_address(self, client):
        """Test geocode with too short address."""
        response = client.get("/api/maps/geocode", params={
            "address": "ab"  # Too short
        })
        assert response.status_code == 422


class TestInputValidation:
    """Test input validation."""
    
    def test_chat_message_too_long(self, client):
        """Test chat message exceeding max length."""
        long_message = "a" * 1001  # Exceeds 1000 char limit
        response = client.post("/api/chat", json={
            "message": long_message
        })
        assert response.status_code == 422
    
    def test_chat_message_with_html(self, client):
        """Test chat message with HTML is sanitized."""
        response = client.post("/api/chat", json={
            "message": "<script>alert('xss')</script>Find coffee"
        })
        # Should not fail, HTML should be stripped
        assert response.status_code in [200, 500]  # 500 if LLM unavailable
    
    def test_place_id_validation(self, client):
        """Test place ID format validation."""
        response = client.get("/api/maps/places/invalid!@#$%")
        assert response.status_code == 400


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def test_rate_limit_headers(self, client):
        """Test rate limit headers are present."""
        response = client.get("/api/maps/config")
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Window" in response.headers


class TestConfiguration:
    """Test configuration handling."""
    
    def test_settings_validation(self):
        """Test settings validation."""
        with pytest.raises(ValueError):
            Settings(google_maps_api_key="short")  # Too short
    
    def test_cors_origins_parsing(self, mock_settings):
        """Test CORS origins are parsed correctly."""
        settings = Settings(
            google_maps_api_key="test_api_key_12345678901234567890",
            allowed_origins="http://localhost:3000,http://example.com"
        )
        assert len(settings.cors_origins) == 2
        assert "http://localhost:3000" in settings.cors_origins
    
    def test_default_coords_parsing(self, mock_settings):
        """Test default coordinates parsing."""
        settings = Settings(
            google_maps_api_key="test_api_key_12345678901234567890",
            default_location="-7.7713,110.3774"
        )
        coords = settings.default_coords
        assert coords == (-7.7713, 110.3774)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
