"""
Google Maps Service.
Handles all interactions with Google Maps APIs with security best practices.
"""

import logging
from typing import Optional
from datetime import datetime
import httpx
from pydantic import BaseModel

from app.config import settings, QuotaTracker

logger = logging.getLogger(__name__)


class PlaceResult(BaseModel):
    """Individual place result from search."""
    place_id: str
    name: str
    address: str
    location: dict  # {lat, lng}
    rating: Optional[float] = None
    total_ratings: Optional[int] = None
    price_level: Optional[int] = None
    types: list[str] = []
    is_open: Optional[bool] = None
    photo_reference: Optional[str] = None
    icon: Optional[str] = None


class PlaceDetails(BaseModel):
    """Detailed information about a place."""
    place_id: str
    name: str
    address: str
    formatted_phone: Optional[str] = None
    website: Optional[str] = None
    location: dict
    rating: Optional[float] = None
    total_ratings: Optional[int] = None
    price_level: Optional[int] = None
    opening_hours: Optional[dict] = None
    reviews: list[dict] = []
    photos: list[str] = []
    types: list[str] = []
    url: Optional[str] = None  # Google Maps URL


class DirectionsResult(BaseModel):
    """Directions between two points."""
    origin: dict
    destination: dict
    distance: str
    duration: str
    steps: list[dict]
    polyline: str  # Encoded polyline for map display
    bounds: dict


class SearchResponse(BaseModel):
    """Response from place search."""
    success: bool
    places: list[PlaceResult] = []
    error: Optional[str] = None
    quota_remaining: Optional[int] = None


class MapsService:
    """
    Service for Google Maps API interactions.
    Implements security best practices and usage tracking.
    """
    
    BASE_URL = "https://maps.googleapis.com/maps/api"
    
    def __init__(self):
        self.api_key = settings.google_maps_api_key
        self.quota_tracker = QuotaTracker(settings.daily_quota_limit)
        self._client: Optional[httpx.AsyncClient] = None
        
        # Validate API key on initialization
        if not self.api_key:
            logger.warning("Google Maps API key not configured!")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _check_quota(self, user_id: str) -> bool:
        """Check if user has remaining API quota."""
        return self.quota_tracker.check_quota(user_id)
    
    def _increment_quota(self, user_id: str, amount: int = 1) -> None:
        """Increment quota usage for user."""
        self.quota_tracker.increment_usage(user_id, amount)
    
    async def search_places(
        self,
        query: str,
        location: Optional[tuple[float, float]] = None,
        radius: int = None,
        place_type: Optional[str] = None,
        user_id: str = "anonymous"
    ) -> SearchResponse:
        """
        Search for places using Google Places API (Text Search).
        
        Args:
            query: Search query (e.g., "italian restaurant")
            location: (lat, lng) tuple for location bias
            radius: Search radius in meters
            place_type: Google place type filter
            user_id: User ID for quota tracking
        """
        # Check quota
        if not self._check_quota(user_id):
            return SearchResponse(
                success=False,
                error="Daily API quota exceeded. Please try again tomorrow.",
                quota_remaining=0
            )
        
        try:
            client = await self._get_client()
            
            # Build request parameters
            params = {
                "query": query,
                "key": self.api_key,
            }
            
            # Add location bias if provided
            if location:
                params["location"] = f"{location[0]},{location[1]}"
                params["radius"] = radius or settings.default_search_radius
            
            # Add type filter if provided
            if place_type:
                params["type"] = place_type
            
            # Make API request
            response = await client.get(
                f"{self.BASE_URL}/place/textsearch/json",
                params=params
            )
            
            # Increment quota
            self._increment_quota(user_id)
            
            if response.status_code != 200:
                logger.error(f"Places API error: {response.status_code}")
                return SearchResponse(
                    success=False,
                    error=f"API request failed: {response.status_code}"
                )
            
            data = response.json()
            
            if data.get("status") not in ["OK", "ZERO_RESULTS"]:
                error_msg = data.get("error_message", data.get("status", "Unknown error"))
                logger.error(f"Places API error: {error_msg}")
                return SearchResponse(
                    success=False,
                    error=error_msg
                )
            
            # Parse results
            places = []
            for result in data.get("results", [])[:settings.max_search_results]:
                place = PlaceResult(
                    place_id=result.get("place_id", ""),
                    name=result.get("name", "Unknown"),
                    address=result.get("formatted_address", ""),
                    location={
                        "lat": result.get("geometry", {}).get("location", {}).get("lat"),
                        "lng": result.get("geometry", {}).get("location", {}).get("lng")
                    },
                    rating=result.get("rating"),
                    total_ratings=result.get("user_ratings_total"),
                    price_level=result.get("price_level"),
                    types=result.get("types", []),
                    is_open=result.get("opening_hours", {}).get("open_now"),
                    photo_reference=result.get("photos", [{}])[0].get("photo_reference") if result.get("photos") else None,
                    icon=result.get("icon")
                )
                places.append(place)
            
            return SearchResponse(
                success=True,
                places=places,
                quota_remaining=self.quota_tracker.get_remaining(user_id)
            )
            
        except httpx.TimeoutException:
            logger.error("Places API request timed out")
            return SearchResponse(
                success=False,
                error="Request timed out. Please try again."
            )
        except Exception as e:
            logger.error(f"Places search error: {e}")
            return SearchResponse(
                success=False,
                error=str(e)
            )
    
    async def get_place_details(
        self,
        place_id: str,
        user_id: str = "anonymous"
    ) -> Optional[PlaceDetails]:
        """
        Get detailed information about a specific place.
        """
        if not self._check_quota(user_id):
            logger.warning(f"Quota exceeded for user {user_id}")
            return None
        
        try:
            client = await self._get_client()
            
            params = {
                "place_id": place_id,
                "key": self.api_key,
                "fields": "place_id,name,formatted_address,formatted_phone_number,"
                         "website,geometry,rating,user_ratings_total,price_level,"
                         "opening_hours,reviews,photos,types,url"
            }
            
            response = await client.get(
                f"{self.BASE_URL}/place/details/json",
                params=params
            )
            
            self._increment_quota(user_id)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            if data.get("status") != "OK":
                return None
            
            result = data.get("result", {})
            
            # Build photo URLs
            photos = []
            for photo in result.get("photos", [])[:5]:
                photo_ref = photo.get("photo_reference")
                if photo_ref:
                    photos.append(
                        f"{self.BASE_URL}/place/photo?maxwidth=400"
                        f"&photo_reference={photo_ref}&key={self.api_key}"
                    )
            
            return PlaceDetails(
                place_id=result.get("place_id", place_id),
                name=result.get("name", ""),
                address=result.get("formatted_address", ""),
                formatted_phone=result.get("formatted_phone_number"),
                website=result.get("website"),
                location={
                    "lat": result.get("geometry", {}).get("location", {}).get("lat"),
                    "lng": result.get("geometry", {}).get("location", {}).get("lng")
                },
                rating=result.get("rating"),
                total_ratings=result.get("user_ratings_total"),
                price_level=result.get("price_level"),
                opening_hours=result.get("opening_hours"),
                reviews=result.get("reviews", [])[:3],
                photos=photos,
                types=result.get("types", []),
                url=result.get("url")
            )
            
        except Exception as e:
            logger.error(f"Place details error: {e}")
            return None
    
    async def get_directions(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        mode: str = "driving",
        user_id: str = "anonymous"
    ) -> Optional[DirectionsResult]:
        """
        Get directions between two points.
        
        Args:
            origin: (lat, lng) starting point
            destination: (lat, lng) ending point
            mode: Travel mode (driving, walking, bicycling, transit)
            user_id: User ID for quota tracking
        """
        if not self._check_quota(user_id):
            return None
        
        try:
            client = await self._get_client()
            
            params = {
                "origin": f"{origin[0]},{origin[1]}",
                "destination": f"{destination[0]},{destination[1]}",
                "mode": mode,
                "key": self.api_key,
            }
            
            response = await client.get(
                f"{self.BASE_URL}/directions/json",
                params=params
            )
            
            self._increment_quota(user_id)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            if data.get("status") != "OK":
                return None
            
            route = data.get("routes", [{}])[0]
            leg = route.get("legs", [{}])[0]
            
            # Parse steps
            steps = []
            for step in leg.get("steps", []):
                steps.append({
                    "instruction": step.get("html_instructions", ""),
                    "distance": step.get("distance", {}).get("text", ""),
                    "duration": step.get("duration", {}).get("text", ""),
                    "travel_mode": step.get("travel_mode", ""),
                    "start_location": step.get("start_location", {}),
                    "end_location": step.get("end_location", {})
                })
            
            return DirectionsResult(
                origin={"lat": origin[0], "lng": origin[1]},
                destination={"lat": destination[0], "lng": destination[1]},
                distance=leg.get("distance", {}).get("text", ""),
                duration=leg.get("duration", {}).get("text", ""),
                steps=steps,
                polyline=route.get("overview_polyline", {}).get("points", ""),
                bounds=route.get("bounds", {})
            )
            
        except Exception as e:
            logger.error(f"Directions error: {e}")
            return None
    
    async def geocode(
        self,
        address: str,
        user_id: str = "anonymous"
    ) -> Optional[dict]:
        """
        Convert address to coordinates.
        """
        if not self._check_quota(user_id):
            return None
        
        try:
            client = await self._get_client()
            
            response = await client.get(
                f"{self.BASE_URL}/geocode/json",
                params={
                    "address": address,
                    "key": self.api_key
                }
            )
            
            self._increment_quota(user_id)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            if data.get("status") != "OK":
                return None
            
            result = data.get("results", [{}])[0]
            location = result.get("geometry", {}).get("location", {})
            
            return {
                "lat": location.get("lat"),
                "lng": location.get("lng"),
                "formatted_address": result.get("formatted_address", "")
            }
            
        except Exception as e:
            logger.error(f"Geocode error: {e}")
            return None
    
    def get_frontend_config(self) -> dict:
        """
        Get configuration for frontend map initialization.
        Returns the frontend API key (if configured) for client-side maps.
        """
        # Use frontend key if available, otherwise provide instructions
        frontend_key = settings.google_maps_frontend_key
        
        if not frontend_key:
            logger.warning("Frontend API key not configured, using backend key")
            frontend_key = self.api_key
        
        return {
            "api_key": frontend_key,
            "default_center": {
                "lat": settings.default_coords[0],
                "lng": settings.default_coords[1]
            },
            "default_zoom": 13
        }


# Global service instance
maps_service = MapsService()
