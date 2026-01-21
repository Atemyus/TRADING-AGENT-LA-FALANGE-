"""
La Falange Trading Platform - Backend API
FastAPI application entry point
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1.routes import ai, auth, trading, positions, analytics, websocket, bot, chart_analysis
from src.api.v1.routes import settings as settings_routes
from src.core.config import settings
from src.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await init_db()

    # Load settings from database and apply to environment
    try:
        from src.core.database import async_session_maker
        from src.api.v1.routes.settings import load_settings_from_db, apply_settings_to_env

        async with async_session_maker() as session:
            db_settings = await load_settings_from_db(session)
            apply_settings_to_env(db_settings)
            print("✅ Settings loaded from database")
    except Exception as e:
        print(f"⚠️ Could not load settings from database: {e}")

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
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ai.router, prefix="/api/v1/ai", tags=["AI Analysis"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(trading.router, prefix="/api/v1/trading", tags=["Trading"])
app.include_router(positions.router, prefix="/api/v1/positions", tags=["Positions"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(websocket.router, prefix="/api/v1/ws", tags=["WebSocket"])
app.include_router(bot.router, prefix="/api/v1", tags=["Bot Control"])
app.include_router(chart_analysis.router, prefix="/api/v1", tags=["Chart Analysis"])
app.include_router(settings_routes.router, prefix="/api/v1/settings", tags=["Settings"])


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
