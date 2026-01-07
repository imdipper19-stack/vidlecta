"""
VideoNotes - FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import redis.asyncio as redis

from app.config import settings
from app.auth.router import router as auth_router
from app.users.router import router as users_router
from app.videos.router import router as videos_router
from app.transcriptions.router import router as transcriptions_router


from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.cleanup_service import cleanup_expired_videos

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events"""
    # Startup
    app.state.redis = redis.from_url(settings.REDIS_URL)
    
    # Initialize Scheduler
    scheduler = AsyncIOScheduler()
    # Run cleanup daily at 3:00 AM
    scheduler.add_job(cleanup_expired_videos, 'cron', hour=3, minute=0)
    scheduler.start()
    app.state.scheduler = scheduler
    
    yield
    
    # Shutdown
    await app.state.redis.close()
    app.state.scheduler.shutdown()


app = FastAPI(
    title="VideoNotes API",
    description="Convert videos to transcriptions and smart summaries",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted Host Middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for load balancer"""
    return {
        "status": "healthy",
        "service": "videonotes-api",
        "version": "1.0.0"
    }


# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users_router, prefix="/api/users", tags=["Users"])
app.include_router(videos_router, prefix="/api/videos", tags=["Videos"])
app.include_router(transcriptions_router, prefix="/api/transcriptions", tags=["Transcriptions"])
