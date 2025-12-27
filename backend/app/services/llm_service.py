"""
LLM Service for Ollama integration.
Handles communication with local LLM and prompt engineering for location queries.
"""

import json
import re
import logging
from typing import Optional
import httpx
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)


class LocationIntent(BaseModel):
    """Parsed user intent for location search."""
    query_type: str  # restaurant, cafe, attraction, parking, etc.
    search_query: str  # Formatted search query for Google Places
    location_hint: Optional[str] = None  # Specific location mentioned
    cuisine_type: Optional[str] = None  # For restaurants
    preferences: list[str] = []  # Additional preferences (cheap, fancy, etc.)
    response_text: str  # Natural language response to user


class LLMResponse(BaseModel):
    """Complete LLM response with parsed data."""
    success: bool
    intent: Optional[LocationIntent] = None
    raw_response: str
    error: Optional[str] = None


class LLMService:
    """
    Service for interacting with Ollama LLM.
    Handles prompt engineering and response parsing.
    """
    
    SYSTEM_PROMPT = """You are a helpful location assistant that helps users find places to go, eat, visit, or explore. 

When a user asks about finding places, you MUST respond with a valid JSON object containing:
1. "query_type": The type of place (restaurant, cafe, bar, attraction, parking, hotel, shop, etc.)
2. "search_query": A search query optimized for Google Places API (e.g., "best sushi restaurant", "coffee shop with wifi")
3. "location_hint": Any specific location mentioned by the user (city, neighborhood, landmark), or null if not specified
4. "cuisine_type": For food places, the specific cuisine (japanese, italian, etc.), or null
5. "preferences": Array of user preferences mentioned (cheap, fancy, romantic, family-friendly, etc.)
6. "response_text": A friendly, helpful response to show the user (2-3 sentences)

IMPORTANT: Always respond with ONLY the JSON object, no additional text before or after.

Example user query: "Where can I find good Italian food near Central Park?"
Example response:
{
    "query_type": "restaurant",
    "search_query": "italian restaurant",
    "location_hint": "Central Park, New York",
    "cuisine_type": "italian",
    "preferences": ["good quality"],
    "response_text": "I'd be happy to help you find great Italian restaurants near Central Park! Let me search for the best options in that area. Here are some highly-rated Italian dining spots for you."
}

Example user query: "I need parking downtown"
Example response:
{
    "query_type": "parking",
    "search_query": "parking garage",
    "location_hint": "downtown",
    "cuisine_type": null,
    "preferences": [],
    "response_text": "I'll help you find convenient parking options downtown. Let me search for available parking facilities in the area."
}

If the user's message is NOT about finding places (e.g., just a greeting or unrelated question), respond with:
{
    "query_type": "general",
    "search_query": "",
    "location_hint": null,
    "cuisine_type": null,
    "preferences": [],
    "response_text": "Your helpful response here"
}"""

    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def check_health(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name", "").split(":")[0] for m in data.get("models", [])]
                return self.model.split(":")[0] in models or any(self.model in m for m in models)
            return False
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False
    
    async def generate_response(self, user_message: str, conversation_history: list[dict] = None) -> LLMResponse:
        """
        Generate LLM response for user message.
        Parses the response to extract location search intent.
        """
        try:
            client = await self._get_client()
            
            # Build messages for chat completion
            messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
            
            # Add conversation history if provided
            if conversation_history:
                for msg in conversation_history[-5:]:  # Keep last 5 messages for context
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            # Call Ollama API
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens,
                    }
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return LLMResponse(
                    success=False,
                    raw_response="",
                    error=f"LLM API error: {response.status_code}"
                )
            
            result = response.json()
            raw_response = result.get("message", {}).get("content", "")
            
            # Parse the JSON response
            intent = self._parse_response(raw_response)
            
            return LLMResponse(
                success=True,
                intent=intent,
                raw_response=raw_response
            )
            
        except httpx.TimeoutException:
            logger.error("Ollama request timed out")
            return LLMResponse(
                success=False,
                raw_response="",
                error="Request timed out. Please try again."
            )
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return LLMResponse(
                success=False,
                raw_response="",
                error=str(e)
            )
    
    def _parse_response(self, raw_response: str) -> Optional[LocationIntent]:
        """Parse LLM response to extract location intent."""
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'\{[\s\S]*\}', raw_response)
            if not json_match:
                logger.warning(f"No JSON found in response: {raw_response[:200]}")
                return LocationIntent(
                    query_type="general",
                    search_query="",
                    response_text=raw_response
                )
            
            json_str = json_match.group()
            data = json.loads(json_str)
            
            return LocationIntent(
                query_type=data.get("query_type", "general"),
                search_query=data.get("search_query", ""),
                location_hint=data.get("location_hint"),
                cuisine_type=data.get("cuisine_type"),
                preferences=data.get("preferences", []),
                response_text=data.get("response_text", "I can help you find places!")
            )
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            # Return a fallback response
            return LocationIntent(
                query_type="general",
                search_query="",
                response_text=raw_response if raw_response else "I'd be happy to help you find places!"
            )
    
    async def extract_search_params(self, user_message: str) -> dict:
        """
        Quick extraction of search parameters without full LLM call.
        Used as fallback or for simple queries.
        """
        message_lower = user_message.lower()
        
        # Simple keyword extraction
        place_types = {
            "restaurant": ["restaurant", "food", "eat", "dinner", "lunch", "breakfast"],
            "cafe": ["cafe", "coffee", "coffeeshop", "starbucks"],
            "bar": ["bar", "pub", "drinks", "beer", "cocktail"],
            "parking": ["parking", "park", "garage"],
            "hotel": ["hotel", "stay", "accommodation", "lodge"],
            "attraction": ["visit", "see", "attraction", "museum", "park", "tourist"],
            "shop": ["shop", "store", "buy", "mall", "shopping"],
            "gas_station": ["gas", "fuel", "petrol"],
            "hospital": ["hospital", "clinic", "doctor", "medical"],
            "pharmacy": ["pharmacy", "drugstore", "medicine"]
        }
        
        detected_type = "point_of_interest"
        for ptype, keywords in place_types.items():
            if any(kw in message_lower for kw in keywords):
                detected_type = ptype
                break
        
        return {
            "query_type": detected_type,
            "search_query": user_message,
            "location_hint": None
        }


# Global service instance
llm_service = LLMService()
