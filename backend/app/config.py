"""
VidLecta - Configuration Settings
Loads all settings from environment variables
"""
from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # ===================
    # Database (PostgreSQL)
    # ===================
    DB_HOST: str = "postgres"
    DB_PORT: int = 5432
    DB_NAME: str = "vidlecta"
    DB_USER: str = "vidlecta_user"
    DB_PASSWORD: str = "password"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # ===================
    # Redis
    # ===================
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    
    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"
    
    # ===================
    # Security
    # ===================
    SECRET_KEY: str = "change-me-in-production-at-least-32-characters"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # ===================
    # CORS & Hosts
    # ===================
    CORS_ORIGINS: List[str] = ["http://localhost", "http://localhost:3000", "https://vidlecta.com"]
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1", "vidlecta.com"]
    
    # ===================
    # MinIO Storage
    # ===================
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "vidlecta_minio"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "vidlecta-uploads"
    MINIO_BUCKET_VIDEOS: str = "videos"
    MINIO_BUCKET_AVATARS: str = "avatars"
    MINIO_BUCKET_AVATARS: str = "avatars"
    MINIO_SECURE: bool = False
    
    # Storage Cleanup
    STORAGE_RETENTION_DAYS: int = 7  # Days to keep raw video files
    ENABLE_CLEANUP_JOB: bool = True
    
    # ===================
    # Whisper AI
    # ===================
    WHISPER_MODEL: str = "small"  # tiny, base, small, medium, large
    
    # ===================
    # Email (SMTP)
    # ===================
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "VidLecta"
    SMTP_FROM_EMAIL: str = "noreply@vidlecta.com"
    SMTP_TLS: bool = True
    
    # MailerSend (recommended)
    MAILERSEND_API_KEY: str = ""
    MAILERSEND_FROM_EMAIL: str = "noreply@vidlecta.com"
    MAILERSEND_FROM_NAME: str = "VidLecta"
    
    # ===================
    # URLs
    # ===================
    FRONTEND_URL: str = "http://localhost"
    API_URL: str = "http://localhost/api"
    
    # ===================
    # Environment
    # ===================
    ENVIRONMENT: str = "development"  # development, staging, production
    DEBUG: bool = True
    
    # ===================
    # Subscription Limits (minutes/month)
    # ===================
    FREE_MINUTES_LIMIT: int = 60
    STUDENT_MINUTES_LIMIT: int = 300
    PRO_MINUTES_LIMIT: int = 999999  # Unlimited
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra env vars


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
