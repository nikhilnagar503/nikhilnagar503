"""
DevOps Pull Request Auto-Orchestrator
Main FastAPI application entry point
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time
from contextlib import asynccontextmanager

from app.config import get_settings
from app.webhook.router import router as webhook_router
from app.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    settings = get_settings()
    setup_logging(settings.log_level)
    logger = logging.getLogger(__name__)
    logger.info("Starting DevOps PR Auto-Orchestrator")
    
    yield
    
    # Shutdown
    logger.info("Shutting down DevOps PR Auto-Orchestrator")


app = FastAPI(
    title="DevOps PR Auto-Orchestrator",
    description="Automated PR analysis and review assistance",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.get("/healthz")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "pr-auto-orchestrator"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "DevOps PR Auto-Orchestrator",
        "version": "1.0.0",
        "docs": "/docs"
    }


# Include webhook routes
app.include_router(webhook_router, prefix="/webhook", tags=["webhooks"])


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.app_env == "dev"
    )