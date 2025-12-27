"""Routes package for Maps LLM application."""

from app.routes.chat import router as chat_router
from app.routes.maps import router as maps_router

__all__ = ["chat_router", "maps_router"]
