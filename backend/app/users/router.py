"""
VideoNotes - Users Router
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
import uuid

from app.database import get_db, User
from app.auth.router import get_current_user
from app.auth.password import PasswordValidator, hash_password, verify_password
from app.auth.schemas import MessageResponse, ChangePasswordRequest


router = APIRouter()


class UpdateProfileRequest(BaseModel):
    """Update profile request"""
    display_name: Optional[str] = None
    username: Optional[str] = None
    bio: Optional[str] = None
    preferred_language: Optional[str] = None
    theme: Optional[str] = None
    email_notifications: Optional[bool] = None
    
    @field_validator("username")
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            import re
            if not re.match(r"^[a-zA-Z0-9_]{3,30}$", v):
                raise ValueError("Username must be 3-30 characters, alphanumeric and underscores only")
        return v.lower() if v else None
    
    @field_validator("preferred_language")
    @classmethod
    def validate_language(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ["en", "ru"]:
            raise ValueError("Language must be 'en' or 'ru'")
        return v
    
    @field_validator("theme")
    @classmethod
    def validate_theme(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ["dark", "light"]:
            raise ValueError("Theme must be 'dark' or 'light'")
        return v


class ChangeEmailRequest(BaseModel):
    """Change email request"""
    new_email: EmailStr
    password: str


class UserProfileResponse(BaseModel):
    """User profile response"""
    id: str
    email: str
    username: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    bio: Optional[str]
    email_verified: bool
    subscription_tier: str
    subscription_expires_at: Optional[datetime]
    monthly_minutes_used: int
    preferred_language: str
    theme: str
    email_notifications: bool
    created_at: datetime


class UserStatsResponse(BaseModel):
    """User statistics response"""
    total_videos: int
    total_transcriptions: int
    total_minutes_processed: float
    monthly_minutes_used: int
    monthly_minutes_limit: int
    subscription_tier: str


@router.get("/me", response_model=UserProfileResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return UserProfileResponse(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        display_name=current_user.display_name,
        avatar_url=current_user.avatar_url,
        bio=current_user.bio,
        email_verified=current_user.email_verified,
        subscription_tier=current_user.subscription_tier,
        subscription_expires_at=current_user.subscription_expires_at,
        monthly_minutes_used=current_user.monthly_minutes_used,
        preferred_language=current_user.preferred_language,
        theme=current_user.theme,
        email_notifications=current_user.email_notifications,
        created_at=current_user.created_at
    )


@router.patch("/me", response_model=UserProfileResponse)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user profile"""
    # Check if new username is taken
    if request.username and request.username != current_user.username:
        result = await db.execute(select(User).where(User.username == request.username))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken"
            )
        current_user.username = request.username
    
    # Update other fields
    if request.display_name is not None:
        current_user.display_name = request.display_name
    if request.bio is not None:
        current_user.bio = request.bio
    if request.preferred_language is not None:
        current_user.preferred_language = request.preferred_language
    if request.theme is not None:
        current_user.theme = request.theme
    if request.email_notifications is not None:
        current_user.email_notifications = request.email_notifications
    
    await db.commit()
    await db.refresh(current_user)
    
    return UserProfileResponse(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        display_name=current_user.display_name,
        avatar_url=current_user.avatar_url,
        bio=current_user.bio,
        email_verified=current_user.email_verified,
        subscription_tier=current_user.subscription_tier,
        subscription_expires_at=current_user.subscription_expires_at,
        monthly_minutes_used=current_user.monthly_minutes_used,
        preferred_language=current_user.preferred_language,
        theme=current_user.theme,
        email_notifications=current_user.email_notifications,
        created_at=current_user.created_at
    )


@router.patch("/me/email", response_model=MessageResponse)
async def change_email(
    request: ChangeEmailRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change user email (requires password confirmation)"""
    # Verify password
    if not verify_password(request.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )
    
    # Check if new email is taken
    result = await db.execute(select(User).where(User.email == request.new_email.lower()))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Update email and mark as unverified
    current_user.email = request.new_email.lower()
    current_user.email_verified = False
    
    await db.commit()
    
    # TODO: Send verification email to new address
    
    return MessageResponse(
        message="Email updated successfully. Please verify your new email address."
    )


@router.patch("/me/password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change user password"""
    # Verify current password
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    # Validate new password strength
    is_valid, errors = PasswordValidator.validate(request.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Password validation failed", "errors": errors}
        )
    
    # Update password
    current_user.password_hash = hash_password(request.new_password)
    
    await db.commit()
    
    return MessageResponse(message="Password changed successfully")


@router.post("/me/avatar", response_model=MessageResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload user avatar"""
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Allowed: JPEG, PNG, GIF, WebP"
        )
    
    # Validate file size (max 5MB)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 5MB"
        )
    
    # TODO: Upload to MinIO storage
    # For now, we'll use a placeholder
    avatar_filename = f"avatars/{current_user.id}/{uuid.uuid4()}.{file.filename.split('.')[-1]}"
    
    # Update user avatar URL
    current_user.avatar_url = f"/storage/{avatar_filename}"
    
    await db.commit()
    
    return MessageResponse(message="Avatar uploaded successfully")


@router.delete("/me/avatar", response_model=MessageResponse)
async def delete_avatar(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete user avatar"""
    # TODO: Delete from MinIO storage
    
    current_user.avatar_url = None
    await db.commit()
    
    return MessageResponse(message="Avatar deleted successfully")
