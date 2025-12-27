"""
Maps routes for Google Maps API interactions.
Provides endpoints for place search, details, and directions.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Query, status

from app.services import maps_service, PlaceDetails, DirectionsResult
from app.utils import (
    PlaceSearchRequest, 
    DirectionsRequest, 
    PlaceDetailsRequest,
    GeocodeRequest
)
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/maps", tags=["Maps"])


@router.get("/places/search")
async def search_places(
    request: Request,
    query: str = Query(..., min_length=1, max_length=500, description="Search query"),
    lat: Optional[float] = Query(None, ge=-90, le=90, description="Latitude"),
    lng: Optional[float] = Query(None, ge=-180, le=180, description="Longitude"),
    radius: Optional[int] = Query(None, ge=100, le=50000, description="Search radius in meters"),
    type: Optional[str] = Query(None, description="Place type filter")
):
    """
    Search for places using Google Places API.
    
    Parameters:
    - query: Search term (e.g., "italian restaurant", "coffee shop")
    - lat, lng: Optional center point for location-biased search
    - radius: Search radius in meters (default: 5000)
    - type: Google place type (restaurant, cafe, etc.)
    
    Returns list of matching places with basic details.
    """
    user_id = request.client.host if request.client else "anonymous"
    
    location = None
    if lat is not None and lng is not None:
        location = (lat, lng)
    
    result = await maps_service.search_places(
        query=query,
        location=location,
        radius=radius,
        place_type=type,
        user_id=user_id
    )
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result.error or "Search failed"
        )
    
    return {
        "success": True,
        "places": [place.model_dump() for place in result.places],
        "count": len(result.places),
        "quota_remaining": result.quota_remaining
    }


@router.get("/places/{place_id}")
async def get_place_details(
    place_id: str,
    request: Request
):
    """
    Get detailed information about a specific place.
    
    Returns:
    - Full address
    - Phone number
    - Website
    - Opening hours
    - Reviews
    - Photos
    - Google Maps URL
    """
    user_id = request.client.host if request.client else "anonymous"
    
    # Validate place_id
    try:
        validated = PlaceDetailsRequest(place_id=place_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid place ID: {str(e)}"
        )
    
    details = await maps_service.get_place_details(
        place_id=validated.place_id,
        user_id=user_id
    )
    
    if not details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Place not found or quota exceeded"
        )
    
    return {
        "success": True,
        "place": details.model_dump()
    }


@router.get("/directions")
async def get_directions(
    request: Request,
    origin_lat: float = Query(..., ge=-90, le=90),
    origin_lng: float = Query(..., ge=-180, le=180),
    dest_lat: float = Query(..., ge=-90, le=90),
    dest_lng: float = Query(..., ge=-180, le=180),
    mode: str = Query("driving", pattern="^(driving|walking|bicycling|transit)$")
):
    """
    Get directions between two points.
    
    Parameters:
    - origin_lat, origin_lng: Starting point coordinates
    - dest_lat, dest_lng: Destination coordinates
    - mode: Travel mode (driving, walking, bicycling, transit)
    
    Returns:
    - Total distance and duration
    - Step-by-step directions
    - Encoded polyline for map display
    """
    user_id = request.client.host if request.client else "anonymous"
    
    directions = await maps_service.get_directions(
        origin=(origin_lat, origin_lng),
        destination=(dest_lat, dest_lng),
        mode=mode,
        user_id=user_id
    )
    
    if not directions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not find directions or quota exceeded"
        )
    
    return {
        "success": True,
        "directions": directions.model_dump()
    }


@router.get("/geocode")
async def geocode_address(
    request: Request,
    address: str = Query(..., min_length=3, max_length=500)
):
    """
    Convert address to coordinates.
    
    Parameters:
    - address: Address string to geocode
    
    Returns:
    - Latitude and longitude
    - Formatted address
    """
    user_id = request.client.host if request.client else "anonymous"
    
    result = await maps_service.geocode(address, user_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not geocode address"
        )
    
    return {
        "success": True,
        "location": result
    }


@router.get("/config")
async def get_maps_config():
    """
    Get frontend map configuration.
    
    Returns the API key and default settings for initializing
    Google Maps on the frontend.
    
    Note: The API key returned is the frontend-restricted key
    configured for client-side use only.
    """
    config = maps_service.get_frontend_config()
    
    return {
        "api_key": config["api_key"],
        "default_center": config["default_center"],
        "default_zoom": config["default_zoom"],
        "map_id": "DEMO_MAP_ID"  # For advanced markers (optional)
    }


@router.get("/photo")
async def get_place_photo(
    photo_reference: str = Query(..., min_length=10),
    max_width: int = Query(400, ge=1, le=1600)
):
    """
    Get URL for a place photo.
    
    Parameters:
    - photo_reference: Photo reference from place search/details
    - max_width: Maximum width of returned image
    
    Returns redirect URL to the photo.
    """
    # Build the photo URL
    photo_url = (
        f"https://maps.googleapis.com/maps/api/place/photo"
        f"?maxwidth={max_width}"
        f"&photo_reference={photo_reference}"
        f"&key={settings.google_maps_api_key}"
    )
    
    return {
        "photo_url": photo_url
    }
