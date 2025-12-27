"""
Input validation utilities.
Ensures all user inputs are properly validated before processing.
"""

import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ChatMessage(BaseModel):
    """Validated chat message from user."""
    message: str = Field(..., min_length=1, max_length=1000)
    location: Optional[str] = Field(None, max_length=200)
    session_id: Optional[str] = Field(None, max_length=100)
    
    @field_validator('message')
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        """Remove potentially harmful content from message."""
        # Remove any script tags or HTML
        v = re.sub(r'<[^>]+>', '', v)
        # Trim whitespace
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        return v
    
    @field_validator('location')
    @classmethod
    def validate_location(cls, v: Optional[str]) -> Optional[str]:
        """Validate location format if provided."""
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        # Basic sanitization
        v = re.sub(r'<[^>]+>', '', v)
        return v


class PlaceSearchRequest(BaseModel):
    """Validated place search request."""
    query: str = Field(..., min_length=1, max_length=500)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    radius: Optional[int] = Field(None, ge=100, le=50000)  # 100m to 50km
    place_type: Optional[str] = Field(None, max_length=50)
    
    @field_validator('query')
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        """Sanitize search query."""
        v = re.sub(r'<[^>]+>', '', v)
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty")
        return v
    
    @field_validator('place_type')
    @classmethod
    def validate_place_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate place type against allowed types."""
        if v is None:
            return None
        
        allowed_types = {
            "restaurant", "cafe", "bar", "food", "lodging", "hotel",
            "parking", "gas_station", "shopping_mall", "store",
            "tourist_attraction", "museum", "park", "hospital",
            "pharmacy", "bank", "atm", "airport", "train_station",
            "bus_station", "subway_station", "point_of_interest"
        }
        
        v = v.lower().strip()
        if v not in allowed_types:
            # Don't raise error, just ignore invalid type
            return None
        return v


class DirectionsRequest(BaseModel):
    """Validated directions request."""
    origin_lat: float = Field(..., ge=-90, le=90)
    origin_lng: float = Field(..., ge=-180, le=180)
    dest_lat: float = Field(..., ge=-90, le=90)
    dest_lng: float = Field(..., ge=-180, le=180)
    mode: str = Field(default="driving")
    
    @field_validator('mode')
    @classmethod
    def validate_mode(cls, v: str) -> str:
        """Validate travel mode."""
        allowed_modes = {"driving", "walking", "bicycling", "transit"}
        v = v.lower().strip()
        if v not in allowed_modes:
            return "driving"
        return v


class PlaceDetailsRequest(BaseModel):
    """Validated place details request."""
    place_id: str = Field(..., min_length=10, max_length=300)
    
    @field_validator('place_id')
    @classmethod
    def validate_place_id(cls, v: str) -> str:
        """Validate place ID format."""
        v = v.strip()
        # Google Place IDs typically start with "ChIJ" for most places
        # But can have other formats, so just do basic validation
        if not re.match(r'^[A-Za-z0-9_-]+$', v):
            raise ValueError("Invalid place ID format")
        return v


class GeocodeRequest(BaseModel):
    """Validated geocode request."""
    address: str = Field(..., min_length=3, max_length=500)
    
    @field_validator('address')
    @classmethod
    def sanitize_address(cls, v: str) -> str:
        """Sanitize address input."""
        v = re.sub(r'<[^>]+>', '', v)
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Address too short")
        return v


def validate_coordinates(lat: float, lng: float) -> bool:
    """Validate latitude and longitude values."""
    return -90 <= lat <= 90 and -180 <= lng <= 180


def parse_location_string(location: str) -> Optional[tuple[float, float]]:
    """
    Parse location string to coordinates.
    Accepts formats: "lat,lng" or "lat, lng"
    """
    try:
        parts = location.split(',')
        if len(parts) != 2:
            return None
        
        lat = float(parts[0].strip())
        lng = float(parts[1].strip())
        
        if validate_coordinates(lat, lng):
            return (lat, lng)
        return None
    except (ValueError, AttributeError):
        return None
