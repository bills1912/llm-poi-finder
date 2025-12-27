# API Documentation

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, the API does not require authentication. Rate limiting is applied per IP address.

## Endpoints

### Health Check

#### GET /health

Check the health status of all services.

**Response:**
```json
{
    "status": "healthy",
    "services": {
        "llm": {
            "status": "up",
            "model": "llama3.2",
            "url": "http://localhost:11434"
        },
        "maps": {
            "status": "configured"
        }
    },
    "version": "1.0.0",
    "environment": "development"
}
```

---

### Chat Endpoints

#### POST /api/chat

Send a natural language message to the LLM and receive location-aware responses.

**Request Body:**
```json
{
    "message": "Where can I find good sushi near Times Square?",
    "location": "40.758,-73.9855",
    "conversation_history": [
        {"role": "user", "content": "Previous message"},
        {"role": "assistant", "content": "Previous response"}
    ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| message | string | Yes | User's query (1-1000 chars) |
| location | string | No | User's location as "lat,lng" |
| conversation_history | array | No | Previous messages for context |

**Response:**
```json
{
    "success": true,
    "message": "I found several great sushi restaurants near Times Square!",
    "places": [
        {
            "place_id": "ChIJ...",
            "name": "Sushi Nakazawa",
            "address": "23 Commerce St, New York, NY",
            "location": {"lat": 40.7322, "lng": -74.0032},
            "rating": 4.7,
            "total_ratings": 1250,
            "price_level": 4,
            "types": ["restaurant", "food"],
            "is_open": true,
            "photo_reference": "...",
            "icon": "..."
        }
    ],
    "has_map_results": true,
    "search_query": "sushi restaurant"
}
```

#### GET /api/chat/health

Check LLM service health specifically.

**Response:**
```json
{
    "llm_available": true,
    "model": "llama3.2",
    "ollama_url": "http://localhost:11434"
}
```

---

### Maps Endpoints

#### GET /api/maps/places/search

Search for places using Google Places API.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| query | string | Yes | Search query |
| lat | float | No | Latitude (-90 to 90) |
| lng | float | No | Longitude (-180 to 180) |
| radius | int | No | Search radius in meters (100-50000) |
| type | string | No | Place type filter |

**Example Request:**
```
GET /api/maps/places/search?query=coffee+shop&lat=40.758&lng=-73.9855&radius=1000
```

**Response:**
```json
{
    "success": true,
    "places": [...],
    "count": 10,
    "quota_remaining": 995
}
```

#### GET /api/maps/places/{place_id}

Get detailed information about a specific place.

**Response:**
```json
{
    "success": true,
    "place": {
        "place_id": "ChIJ...",
        "name": "Starbucks",
        "address": "123 Main St, New York, NY",
        "formatted_phone": "+1 212-555-1234",
        "website": "https://www.starbucks.com",
        "location": {"lat": 40.758, "lng": -73.9855},
        "rating": 4.2,
        "total_ratings": 500,
        "price_level": 2,
        "opening_hours": {
            "open_now": true,
            "weekday_text": [
                "Monday: 6:00 AM – 9:00 PM",
                "..."
            ]
        },
        "reviews": [...],
        "photos": ["https://..."],
        "types": ["cafe", "food"],
        "url": "https://maps.google.com/?cid=..."
    }
}
```

#### GET /api/maps/directions

Get directions between two points.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| origin_lat | float | Yes | Origin latitude |
| origin_lng | float | Yes | Origin longitude |
| dest_lat | float | Yes | Destination latitude |
| dest_lng | float | Yes | Destination longitude |
| mode | string | No | Travel mode (driving, walking, bicycling, transit) |

**Response:**
```json
{
    "success": true,
    "directions": {
        "origin": {"lat": 40.758, "lng": -73.9855},
        "destination": {"lat": 40.748, "lng": -73.9857},
        "distance": "0.7 mi",
        "duration": "15 mins",
        "steps": [
            {
                "instruction": "Head south on Broadway",
                "distance": "0.2 mi",
                "duration": "5 mins"
            }
        ],
        "polyline": "encoded_polyline_string",
        "bounds": {...}
    }
}
```

#### GET /api/maps/geocode

Convert an address to coordinates.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| address | string | Yes | Address to geocode |

**Response:**
```json
{
    "success": true,
    "location": {
        "lat": 40.758,
        "lng": -73.9855,
        "formatted_address": "Times Square, New York, NY, USA"
    }
}
```

#### GET /api/maps/config

Get frontend map configuration.

**Response:**
```json
{
    "api_key": "AIza...",
    "default_center": {"lat": -7.7713, "lng": 110.3774},
    "default_zoom": 13,
    "map_id": "DEMO_MAP_ID"
}
```

---

## Error Responses

All endpoints return consistent error responses:

```json
{
    "success": false,
    "error": "Error message here",
    "detail": "Additional details (only in debug mode)"
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid input |
| 404 | Not Found |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

---

## Rate Limiting

- **Limit:** 100 requests per hour per IP
- **Headers:**
  - `X-RateLimit-Limit`: Maximum requests per window
  - `X-RateLimit-Window`: Time window in seconds
  - `Retry-After`: Seconds to wait (when rate limited)

---

## Best Practices

1. **Cache responses** when possible to reduce API calls
2. **Use location parameter** for more relevant results
3. **Handle errors gracefully** with appropriate user feedback
4. **Respect rate limits** to avoid service interruption
5. **Use conversation history** for better context in chat
