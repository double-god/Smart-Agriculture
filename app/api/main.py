"""
FastAPI Main Application for Smart Agriculture System.

This module initializes the FastAPI application with all routes and middleware.
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.api.endpoints.taxonomy import router as taxonomy_router
from app.api.endpoints.upload import router as upload_router
from app.api.endpoints.diagnose import router as diagnose_router

# Initialize settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Plant Disease and Pest Diagnosis System",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Register routers
app.include_router(taxonomy_router)
app.include_router(upload_router)
app.include_router(diagnose_router)


@app.get("/")
async def root():
    """Root endpoint with system information."""
    return {
        "message": "Smart Agriculture API",
        "version": "0.1.0",
        "status": "operational",
    }


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint for Docker health checks."""
    return {"status": "healthy", "service": "smart-agriculture-web"}


@app.get("/api/v1/info")
async def system_info():
    """System information endpoint."""
    return {
        "app_name": settings.app_name,
        "version": "0.1.0",
        "debug": settings.debug,
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle all uncaught exceptions."""
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )
