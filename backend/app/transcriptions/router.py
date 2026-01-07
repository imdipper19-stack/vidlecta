"""
VideoNotes - Transcriptions Router
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

from app.database import get_db, User, Video, Transcription
from app.auth.router import get_current_user


router = APIRouter()


class TranscriptionResponse(BaseModel):
    """Transcription response schema"""
    id: str
    video_id: str
    language: str
    text: str
    summary: Optional[str]
    word_count: Optional[int]
    confidence_score: Optional[float]
    processing_time_seconds: Optional[float]
    created_at: datetime


class TranscriptionListResponse(BaseModel):
    """Transcription list response"""
    transcriptions: List[TranscriptionResponse]
    total: int


class CreateTranscriptionRequest(BaseModel):
    """Create transcription request"""
    video_id: str
    language: str = "en"


@router.post("", response_model=TranscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_transcription(
    request: CreateTranscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Request a new transcription for a video.
    
    Supported languages: en (English), ru (Russian)
    """
    # Validate language
    if request.language not in ["en", "ru"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supported languages: en (English), ru (Russian)"
        )
    
    # Check if video exists and belongs to user
    result = await db.execute(
        select(Video).where(
            Video.id == uuid.UUID(request.video_id),
            Video.user_id == current_user.id
        )
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    if video.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video is not yet processed"
        )
    
    # Check if transcription already exists for this language
    existing = await db.execute(
        select(Transcription).where(
            Transcription.video_id == video.id,
            Transcription.language == request.language
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Transcription in {request.language} already exists for this video"
        )
    
    # Create transcription (in real app, this would trigger Celery task)
    transcription = Transcription(
        video_id=video.id,
        user_id=current_user.id,
        language=request.language,
        text="Transcription processing...",  # Placeholder
        word_count=0
    )
    
    db.add(transcription)
    await db.commit()
    await db.refresh(transcription)
    
    # TODO: Trigger Celery task
    # transcribe_video.delay(str(transcription.id))
    
    return TranscriptionResponse(
        id=str(transcription.id),
        video_id=str(transcription.video_id),
        language=transcription.language,
        text=transcription.text,
        summary=transcription.summary,
        word_count=transcription.word_count,
        confidence_score=transcription.confidence_score,
        processing_time_seconds=transcription.processing_time_seconds,
        created_at=transcription.created_at
    )


@router.get("", response_model=TranscriptionListResponse)
async def list_transcriptions(
    video_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all transcriptions for current user"""
    query = select(Transcription).where(Transcription.user_id == current_user.id)
    
    if video_id:
        query = query.where(Transcription.video_id == uuid.UUID(video_id))
    
    query = query.order_by(Transcription.created_at.desc())
    
    result = await db.execute(query)
    transcriptions = result.scalars().all()
    
    return TranscriptionListResponse(
        transcriptions=[
            TranscriptionResponse(
                id=str(t.id),
                video_id=str(t.video_id),
                language=t.language,
                text=t.text,
                summary=t.summary,
                word_count=t.word_count,
                confidence_score=t.confidence_score,
                processing_time_seconds=t.processing_time_seconds,
                created_at=t.created_at
            )
            for t in transcriptions
        ],
        total=len(transcriptions)
    )


@router.get("/{transcription_id}", response_model=TranscriptionResponse)
async def get_transcription(
    transcription_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get transcription details"""
    result = await db.execute(
        select(Transcription).where(
            Transcription.id == uuid.UUID(transcription_id),
            Transcription.user_id == current_user.id
        )
    )
    transcription = result.scalar_one_or_none()
    
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcription not found"
        )
    
    return TranscriptionResponse(
        id=str(transcription.id),
        video_id=str(transcription.video_id),
        language=transcription.language,
        text=transcription.text,
        summary=transcription.summary,
        word_count=transcription.word_count,
        confidence_score=transcription.confidence_score,
        processing_time_seconds=transcription.processing_time_seconds,
        created_at=transcription.created_at
    )


@router.get("/{transcription_id}/summary")
async def get_summary(
    transcription_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get AI-generated summary for transcription"""
    result = await db.execute(
        select(Transcription).where(
            Transcription.id == uuid.UUID(transcription_id),
            Transcription.user_id == current_user.id
        )
    )
    transcription = result.scalar_one_or_none()
    
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcription not found"
        )
    
    if not transcription.summary:
        # TODO: Generate summary using AI
        return {"summary": None, "message": "Summary is being generated..."}
    
    return {
        "transcription_id": str(transcription.id),
        "summary": transcription.summary,
        "language": transcription.language
    }


@router.delete("/{transcription_id}")
async def delete_transcription(
    transcription_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a transcription"""
    result = await db.execute(
        select(Transcription).where(
            Transcription.id == uuid.UUID(transcription_id),
            Transcription.user_id == current_user.id
        )
    )
    transcription = result.scalar_one_or_none()
    
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcription not found"
        )
    
    await db.delete(transcription)
    await db.commit()
    
    return {"message": "Transcription deleted successfully"}
