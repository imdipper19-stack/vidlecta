"""
VideoNotes - Storage Cleanup Service
Handles deletion of old video files to save storage space
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from minio import Minio

from app.database import Video, async_session
from app.config import settings

# Setup logger
logger = logging.getLogger("cleanup_service")
logging.basicConfig(level=logging.INFO)

async def cleanup_expired_videos():
    """
    Delete video files older than STORAGE_RETENTION_DAYS from MinIO
    and update their status to 'archived' in the database.
    """
    if not settings.ENABLE_CLEANUP_JOB:
        logger.info("Cleanup job is disabled in settings")
        return

    days = settings.STORAGE_RETENTION_DAYS
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    logger.info(f"Starting storage cleanup for videos older than {days} days (before {cutoff_date})")
    
    # Initialize MinIO client
    minio_client = Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE
    )
    
    async with async_session() as db:
        try:
            # Find eligible videos
            # Status should not be 'archived' and created_at < cutoff_date
            query = select(Video).where(
                and_(
                    Video.created_at < cutoff_date,
                    Video.status != 'archived'
                )
            )
            
            result = await db.execute(query)
            videos_to_archive = result.scalars().all()
            
            if not videos_to_archive:
                logger.info("No expired videos found")
                return
            
            logger.info(f"Found {len(videos_to_archive)} videos to archive")
            
            success_count = 0
            space_reclaimed = 0
            
            for video in videos_to_archive:
                try:
                    # 1. Delete from MinIO
                    # The storage_path usually looks like "videos/user_id/video_id/filename"
                    # We need to make sure we use the correct bucket and object name
                    
                    # Assuming storage_path is the object name relative to the bucket
                    object_name = video.storage_path
                    
                    try:
                        minio_client.remove_object(settings.MINIO_BUCKET, object_name)
                        # Also try to remove the folder if empty? MinIO doesn't have folders really.
                        # We might want to remove the specific folder for this video if it exists
                    except Exception as e:
                        logger.warning(f"Failed to delete file from MinIO {object_name}: {e}")
                        # Continue anyway to mark as archived if file doesn't exist?
                        # Maybe it was already deleted manually.
                    
                    # 2. Update status in Database
                    video.status = 'archived'
                    # Clear storage path to indicate file is gone? 
                    # Optionally we can keep it for reference or clear it.
                    # video.storage_path = "" 
                    
                    success_count += 1
                    space_reclaimed += video.file_size
                    
                except Exception as e:
                    logger.error(f"Error processing video {video.id}: {e}")
            
            await db.commit()
            
            # Convert bytes to MB/GB for logging
            space_mb = space_reclaimed / (1024 * 1024)
            logger.info(f"Cleanup completed. Archived {success_count} videos. Reclaimed {space_mb:.2f} MB")
            
        except Exception as e:
            logger.error(f"Cleanup job failed: {e}")
            await db.rollback()
