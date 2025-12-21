"""
La Falange Trading Platform - Backend API
FastAPI application entry point
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1.routes import auth, trading, positions, analytics, websocket
from src.core.config import settings
from src.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await init_db()
    print(f"🚀 La Falange Trading Platform v{settings.VERSION} started")
    print(f"📊 Environment: {settings.ENVIRONMENT}")
    yield
    # Shutdown
    print("👋 Shutting down...")


app = FastAPI(
    title="La Falange Trading Platform",
    description="AI-Powered CFD/Futures Trading Platform",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/api/redoc" if settings.ENVIRONMENT != "production" else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(trading.router, prefix="/api/v1/trading", tags=["Trading"])
app.include_router(positions.router, prefix="/api/v1/positions", tags=["Positions"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(websocket.router, prefix="/api/v1/ws", tags=["WebSocket"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "La Falange Trading Platform",
        "version": settings.VERSION,
        "docs": "/api/docs",
    }
