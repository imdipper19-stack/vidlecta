"""
VideoNotes Celery Application Configuration
"""
from celery import Celery
from .config import settings

# Create Celery app
celery_app = Celery(
    "videonotes",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks"]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,  # Acknowledge after task completes
    task_reject_on_worker_lost=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time for Whisper
    worker_concurrency=2,  # Limit concurrent tasks
    
    # Task time limits
    task_soft_time_limit=1800,  # 30 minutes soft limit
    task_time_limit=3600,  # 1 hour hard limit
    
    # Result backend settings
    result_expires=86400,  # Results expire in 24 hours
    
    # Task routing
    task_routes={
        "app.tasks.transcribe_video": {"queue": "transcription"},
        "app.tasks.generate_summary": {"queue": "summary"},
        "app.tasks.cleanup_temp_files": {"queue": "cleanup"},
    },
    
    # Default queue
    task_default_queue="default",
)

# Optional: Set up beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "cleanup-temp-files-daily": {
        "task": "app.tasks.cleanup_temp_files",
        "schedule": 86400.0,  # Run daily
    },
}
