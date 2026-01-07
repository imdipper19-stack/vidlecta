"""
VideoNotes - Authentication Router
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from typing import Optional
import uuid

from app.database import get_db, User, Session
from app.auth.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, RefreshTokenRequest,
    ForgotPasswordRequest, ResetPasswordRequest, UserResponse,
    PasswordValidationResponse, MessageResponse
)
from app.auth.password import (
    PasswordValidator, hash_password, verify_password
)
from app.auth.jwt import (
    create_access_token, create_refresh_token, verify_token,
    create_email_verification_token, create_password_reset_token
)
from app.config import settings


router = APIRouter()
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    payload = verify_token(token, "access")
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Get user from database
    result = await db.execute(select(User).where(User.id == uuid.UUID(payload.sub)))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user account.
    
    Password requirements:
    - Minimum 8 characters
    - At least 1 uppercase letter (A-Z)
    - At least 1 lowercase letter (a-z)
    - At least 1 digit (0-9)
    - At least 1 special character (!@#$%^&*)
    """
    # Validate password strength
    is_valid, errors = PasswordValidator.validate(request.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Password validation failed", "errors": errors}
        )
    
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == request.email.lower()))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Check if username already exists
    result = await db.execute(select(User).where(User.username == request.username.lower()))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken"
        )
    
    # Create new user
    user = User(
        email=request.email.lower(),
        username=request.username.lower(),
        display_name=request.display_name or request.username,
        password_hash=hash_password(request.password),
        subscription_tier="free",
        monthly_minutes_reset_at=datetime.utcnow()
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # TODO: Send email verification
    # verification_token = create_email_verification_token(str(user.id))
    # await send_verification_email(user.email, verification_token)
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        bio=user.bio,
        email_verified=user.email_verified,
        subscription_tier=user.subscription_tier,
        monthly_minutes_used=user.monthly_minutes_used,
        preferred_language=user.preferred_language,
        theme=user.theme,
        created_at=user.created_at
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    req: Request,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user and return JWT tokens"""
    # Find user by email
    result = await db.execute(select(User).where(User.email == request.email.lower()))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    # Create tokens
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    
    # Store refresh token in session
    expires_at = datetime.utcnow() + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS if request.remember_me else 1
    )
    
    session = Session(
        user_id=user.id,
        refresh_token=refresh_token,
        ip_address=req.client.host if req.client else None,
        user_agent=req.headers.get("user-agent"),
        expires_at=expires_at
    )
    
    db.add(session)
    
    # Update last login
    user.last_login_at = datetime.utcnow()
    
    await db.commit()
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token"""
    payload = verify_token(request.refresh_token, "refresh")
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Verify session exists in database
    result = await db.execute(
        select(Session).where(Session.refresh_token == request.refresh_token)
    )
    session = result.scalar_one_or_none()
    
    if not session or session.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired, please login again"
        )
    
    # Create new access token
    access_token = create_access_token(payload.sub)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=request.refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Logout user by invalidating refresh token"""
    result = await db.execute(
        select(Session).where(Session.refresh_token == request.refresh_token)
    )
    session = result.scalar_one_or_none()
    
    if session:
        await db.delete(session)
        await db.commit()
    
    return MessageResponse(message="Successfully logged out")


@router.post("/validate-password", response_model=PasswordValidationResponse)
async def validate_password(password: str):
    """
    Validate password strength (for real-time frontend validation).
    Does not require authentication.
    """
    is_valid, errors = PasswordValidator.validate(password)
    strength_score = PasswordValidator.get_strength_score(password)
    strength_label = PasswordValidator.get_strength_label(password)
    
    return PasswordValidationResponse(
        is_valid=is_valid,
        errors=errors,
        strength_score=strength_score,
        strength_label=strength_label
    )


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """Request password reset email"""
    result = await db.execute(select(User).where(User.email == request.email.lower()))
    user = result.scalar_one_or_none()
    
    # Always return success to prevent email enumeration
    if user:
        reset_token = create_password_reset_token(str(user.id))
        # TODO: Send password reset email
        # await send_password_reset_email(user.email, reset_token)
    
    return MessageResponse(
        message="If an account exists with this email, you will receive a password reset link"
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """Reset password using reset token"""
    payload = verify_token(request.token, "password_reset")
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Validate new password
    is_valid, errors = PasswordValidator.validate(request.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Password validation failed", "errors": errors}
        )
    
    # Update user password
    result = await db.execute(select(User).where(User.id == uuid.UUID(payload.sub)))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.password_hash = hash_password(request.password)
    
    # Invalidate all sessions
    await db.execute(
        select(Session).where(Session.user_id == user.id)
    )
    
    await db.commit()
    
    return MessageResponse(message="Password has been reset successfully")


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user profile"""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        display_name=current_user.display_name,
        avatar_url=current_user.avatar_url,
        bio=current_user.bio,
        email_verified=current_user.email_verified,
        subscription_tier=current_user.subscription_tier,
        monthly_minutes_used=current_user.monthly_minutes_used,
        preferred_language=current_user.preferred_language,
        theme=current_user.theme,
        created_at=current_user.created_at
    )
