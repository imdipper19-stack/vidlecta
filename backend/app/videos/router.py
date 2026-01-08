"""
VideoNotes - Videos Router
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

from app.database import get_db, User, Video, Transcription
from app.auth.router import get_current_user
from app.config import settings


router = APIRouter()


class VideoResponse(BaseModel):
    """Video response schema"""
    id: str
    original_filename: str
    file_size: int
    duration_seconds: Optional[int]
    status: str
    error_message: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]
    transcription_count: int = 0


class VideoListResponse(BaseModel):
    """Video list response"""
    videos: List[VideoResponse]
    total: int
    page: int
    per_page: int


class VideoUploadResponse(BaseModel):
    """Video upload response"""
    id: str
    message: str
    status: str


class VideoFromUrlRequest(BaseModel):
    """Request to upload video from URL"""
    url: str
    language: str = "en"


class VideoFromUrlResponse(BaseModel):
    """Response for URL upload"""
    id: str
    message: str
    status: str
    source_url: str


def get_minutes_limit(tier: str) -> int:
    """Get monthly minutes limit for subscription tier"""
    limits = {
        "free": settings.FREE_MINUTES_LIMIT,
        "student": settings.STUDENT_MINUTES_LIMIT,
        "pro": settings.PRO_MINUTES_LIMIT
    }
    return limits.get(tier, settings.FREE_MINUTES_LIMIT)


@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    language: str = "en",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a video for transcription.
    
    Supported formats: MP4, MOV, AVI, MKV, WebM, MP3, WAV, M4A
    Maximum file size: 1GB
    """
    # Check subscription limits
    minutes_limit = get_minutes_limit(current_user.subscription_tier)
    if current_user.monthly_minutes_used >= minutes_limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Monthly limit reached ({minutes_limit} minutes). Please upgrade your plan."
        )
    
    # Validate file type
    allowed_types = [
        "video/mp4", "video/quicktime", "video/x-msvideo", "video/x-matroska",
        "video/webm", "audio/mpeg", "audio/wav", "audio/x-m4a", "audio/mp3"
    ]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Supported: MP4, MOV, AVI, MKV, WebM, MP3, WAV, M4A"
        )
    
    # Validate language
    if language not in ["en", "ru"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supported languages: en (English), ru (Russian)"
        )
    
    # Read file
    contents = await file.read()
    file_size = len(contents)
    
    # Validate file size (max 1GB)
    if file_size > 1024 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 1GB"
        )
    
    # Create video record
    video_id = uuid.uuid4()
    storage_path = f"videos/{current_user.id}/{video_id}/{file.filename}"
    
    video = Video(
        id=video_id,
        user_id=current_user.id,
        original_filename=file.filename,
        storage_path=storage_path,
        file_size=file_size,
        status="pending"
    )
    
    db.add(video)
    await db.commit()
    
    # Save file to temporary location for processing
    import tempfile
    import os
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, file.filename)
    with open(temp_file_path, "wb") as f:
        f.write(contents)
    
    # Trigger Celery task for transcription
    from app.tasks import transcribe_video
    transcribe_video.delay(str(video_id), temp_file_path, language)
    
    return VideoUploadResponse(
        id=str(video_id),
        message="Video uploaded successfully. Processing will begin shortly.",
        status="pending"
    )


@router.post("/from-url", response_model=VideoFromUrlResponse)
async def upload_from_url(
    request: VideoFromUrlRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload video from URL (YouTube, VK, RuTube, TikTok, etc.)
    
    Supported platforms: YouTube, VK Video, RuTube, TikTok, Vimeo, and 1000+ more.
    """
    import re
    from app.tasks import download_from_url
    
    # Check subscription limits
    minutes_limit = get_minutes_limit(current_user.subscription_tier)
    if current_user.monthly_minutes_used >= minutes_limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Monthly limit reached ({minutes_limit} minutes). Please upgrade your plan."
        )
    
    # Validate URL format
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    
    if not url_pattern.match(request.url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid URL format"
        )
    
    # Validate language
    if request.language not in ["en", "ru", "auto"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supported languages: en (English), ru (Russian), auto (detect)"
        )
    
    # Create video record
    video_id = uuid.uuid4()
    
    video = Video(
        id=video_id,
        user_id=current_user.id,
        original_filename=f"from_url_{video_id}",  # Will be updated after download
        storage_path=f"videos/{current_user.id}/{video_id}/",
        file_size=0,  # Will be updated after download
        status="queued",
        source_url=request.url
    )
    
    db.add(video)
    await db.commit()
    
    # Trigger Celery task for download and transcription
    download_from_url.delay(str(video_id), request.url, request.language)
    
    return VideoFromUrlResponse(
        id=str(video_id),
        message="Video queued for download. Transcription will begin after download completes.",
        status="queued",
        source_url=request.url
    )


@router.get("", response_model=VideoListResponse)
async def list_videos(
    page: int = 1,
    per_page: int = 20,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all videos for current user"""
    # Build query
    query = select(Video).where(Video.user_id == current_user.id)
    
    if status_filter:
        query = query.where(Video.status == status_filter)
    
    query = query.order_by(Video.created_at.desc())
    
    # Get total count
    count_query = select(func.count()).select_from(Video).where(Video.user_id == current_user.id)
    if status_filter:
        count_query = count_query.where(Video.status == status_filter)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Paginate
    query = query.offset((page - 1) * per_page).limit(per_page)
    
    result = await db.execute(query)
    videos = result.scalars().all()
    
    # Build response
    video_responses = []
    for video in videos:
        # Get transcription count
        trans_count_result = await db.execute(
            select(func.count()).select_from(Transcription).where(Transcription.video_id == video.id)
        )
        trans_count = trans_count_result.scalar()
        
        video_responses.append(VideoResponse(
            id=str(video.id),
            original_filename=video.original_filename,
            file_size=video.file_size,
            duration_seconds=video.duration_seconds,
            status=video.status,
            error_message=video.error_message,
            created_at=video.created_at,
            processed_at=video.processed_at,
            transcription_count=trans_count
        ))
    
    return VideoListResponse(
        videos=video_responses,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get video details"""
    result = await db.execute(
        select(Video).where(
            Video.id == uuid.UUID(video_id),
            Video.user_id == current_user.id
        )
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    # Get transcription count
    trans_count_result = await db.execute(
        select(func.count()).select_from(Transcription).where(Transcription.video_id == video.id)
    )
    trans_count = trans_count_result.scalar()
    
    return VideoResponse(
        id=str(video.id),
        original_filename=video.original_filename,
        file_size=video.file_size,
        duration_seconds=video.duration_seconds,
        status=video.status,
        error_message=video.error_message,
        created_at=video.created_at,
        processed_at=video.processed_at,
        transcription_count=trans_count
    )


@router.delete("/{video_id}")
async def delete_video(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a video and its transcriptions"""
    result = await db.execute(
        select(Video).where(
            Video.id == uuid.UUID(video_id),
            Video.user_id == current_user.id
        )
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    # TODO: Delete from MinIO storage
    
    await db.delete(video)
    await db.commit()
    
    return {"message": "Video deleted successfully"}
