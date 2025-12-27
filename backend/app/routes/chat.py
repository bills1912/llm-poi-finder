"""
Chat routes for LLM interaction.
Handles user messages and returns location-aware responses.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from app.services import llm_service, maps_service, PlaceResult
from app.utils import ChatMessage, parse_location_string
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])


class ChatResponse(BaseModel):
    """Response from chat endpoint."""
    success: bool
    message: str  # Natural language response
    places: list[PlaceResult] = []  # Found places
    has_map_results: bool = False
    search_query: Optional[str] = None
    error: Optional[str] = None


class ConversationMessage(BaseModel):
    """Message in conversation history."""
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Extended chat request with conversation history."""
    message: str
    location: Optional[str] = None
    conversation_history: list[ConversationMessage] = []


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request):
    """
    Send a message to the LLM and get location-aware response.
    
    The LLM will:
    1. Understand the user's intent (finding places to eat, visit, etc.)
    2. Extract relevant search parameters
    3. Search Google Maps for matching places
    4. Return a helpful response with place recommendations
    """
    # Get user ID for quota tracking (from IP in this demo)
    user_id = req.client.host if req.client else "anonymous"
    
    try:
        # Validate input
        validated = ChatMessage(
            message=request.message,
            location=request.location
        )
        
        # Convert conversation history format
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.conversation_history
        ]
        
        # Get LLM response
        llm_response = await llm_service.generate_response(
            validated.message,
            conversation_history=history
        )
        
        if not llm_response.success:
            logger.error(f"LLM error: {llm_response.error}")
            return ChatResponse(
                success=False,
                message="I'm having trouble processing your request. Please try again.",
                error=llm_response.error
            )
        
        # Check if this is a location query
        intent = llm_response.intent
        
        if not intent or intent.query_type == "general" or not intent.search_query:
            # Not a location query, return LLM response directly
            return ChatResponse(
                success=True,
                message=intent.response_text if intent else "How can I help you find places today?",
                has_map_results=False
            )
        
        # This is a location query - search for places
        location = None
        
        # Try to get location from user's input
        if validated.location:
            location = parse_location_string(validated.location)
        
        # If location hint from LLM, geocode it
        if not location and intent.location_hint:
            geocoded = await maps_service.geocode(intent.location_hint, user_id)
            if geocoded:
                location = (geocoded["lat"], geocoded["lng"])
        
        # Fall back to default location
        if not location:
            location = settings.default_coords
        
        # Build search query
        search_query = intent.search_query
        if intent.cuisine_type:
            search_query = f"{intent.cuisine_type} {search_query}"
        
        # Search for places
        search_result = await maps_service.search_places(
            query=search_query,
            location=location,
            place_type=intent.query_type if intent.query_type != "general" else None,
            user_id=user_id
        )
        
        if not search_result.success:
            return ChatResponse(
                success=True,
                message=f"{intent.response_text} However, I couldn't find any results. {search_result.error or 'Please try a different search.'}",
                has_map_results=False,
                search_query=search_query
            )
        
        if not search_result.places:
            return ChatResponse(
                success=True,
                message=f"{intent.response_text} Unfortunately, I couldn't find any places matching your criteria. Try broadening your search or checking a different area.",
                has_map_results=False,
                search_query=search_query
            )
        
        # Build response message with place summary
        place_count = len(search_result.places)
        response_message = intent.response_text
        
        if place_count > 0:
            top_places = search_result.places[:3]
            place_names = ", ".join([p.name for p in top_places])
            response_message += f" I found {place_count} places for you. Top recommendations include: {place_names}."
        
        return ChatResponse(
            success=True,
            message=response_message,
            places=search_result.places,
            has_map_results=True,
            search_query=search_query
        )
        
    except Exception as e:
        logger.exception(f"Chat error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred processing your request"
        )


@router.get("/health")
async def chat_health():
    """Check LLM service health."""
    is_healthy = await llm_service.check_health()
    
    return {
        "llm_available": is_healthy,
        "model": settings.llm_model,
        "ollama_url": settings.ollama_base_url
    }
