"""
HeyPico Maps LLM - Main Application Entry Point

A local LLM-powered location finder with Google Maps integration.
This FastAPI application provides:
- Chat endpoint for natural language location queries
- Google Maps integration for place search and directions
- Rate limiting and security best practices
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routes import chat_router, maps_router
from app.middleware import RateLimitMiddleware, RateLimiter
from app.services import llm_service, maps_service

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Manages startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"LLM Model: {settings.llm_model}")
    logger.info(f"Ollama URL: {settings.ollama_base_url}")
    
    # Check LLM availability
    llm_available = await llm_service.check_health()
    if llm_available:
        logger.info("✓ LLM service is available")
    else:
        logger.warning("✗ LLM service is not available - chat features may not work")
    
    # Check API key configuration
    if settings.google_maps_api_key:
        masked_key = f"{settings.google_maps_api_key[:4]}...{settings.google_maps_api_key[-4:]}"
        logger.info(f"✓ Google Maps API key configured: {masked_key}")
    else:
        logger.warning("✗ Google Maps API key not configured!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    await llm_service.close()
    await maps_service.close()
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="""
    A local LLM-powered location finder with Google Maps integration.
    
    ## Features
    - Natural language queries for finding places
    - Google Maps integration with embedded maps
    - Directions and navigation
    - Rate limiting and security best practices
    
    ## Usage
    1. Send a message to `/api/chat` asking about places
    2. View results on the embedded map
    3. Get directions to any location
    """,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
rate_limiter = RateLimiter(
    requests_per_window=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window
)
app.add_middleware(
    RateLimitMiddleware,
    limiter=rate_limiter,
    exclude_paths=["/health", "/docs", "/openapi.json", "/redoc", "/"]
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions gracefully."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "An unexpected error occurred",
            "detail": str(exc) if settings.debug else None
        }
    )


# Include routers
app.include_router(chat_router)
app.include_router(maps_router)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Local LLM-powered location finder with Google Maps",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    Returns status of all services.
    """
    llm_status = await llm_service.check_health()
    maps_configured = bool(settings.google_maps_api_key)
    
    all_healthy = llm_status and maps_configured
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": {
            "llm": {
                "status": "up" if llm_status else "down",
                "model": settings.llm_model,
                "url": settings.ollama_base_url
            },
            "maps": {
                "status": "configured" if maps_configured else "not_configured"
            }
        },
        "version": settings.app_version,
        "environment": settings.environment
    }


# For running directly with: python -m app.main
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
