"""
VideoNotes - Pydantic Schemas for Authentication
"""
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime
import re


class RegisterRequest(BaseModel):
    """Registration request schema with validation"""
    email: EmailStr
    username: str
    display_name: Optional[str] = None
    password: str
    password_confirm: str
    
    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        # 3-30 characters, alphanumeric and underscores only
        if not re.match(r"^[a-zA-Z0-9_]{3,30}$", v):
            raise ValueError(
                "Username must be 3-30 characters and contain only letters, numbers, and underscores"
            )
        # Cannot be all numbers
        if v.isdigit():
            raise ValueError("Username cannot be all numbers")
        # Cannot start with underscore
        if v.startswith("_"):
            raise ValueError("Username cannot start with an underscore")
        return v.lower()
    
    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            # 2-50 characters
            if len(v) < 2 or len(v) > 50:
                raise ValueError("Display name must be 2-50 characters")
        return v
    
    @field_validator("password_confirm")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v


class LoginRequest(BaseModel):
    """Login request schema"""
    email: EmailStr
    password: str
    remember_me: bool = False


class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema"""
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    """Forgot password request schema"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password request schema"""
    token: str
    password: str
    password_confirm: str
    
    @field_validator("password_confirm")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v


class ChangePasswordRequest(BaseModel):
    """Change password request schema"""
    current_password: str
    new_password: str
    new_password_confirm: str
    
    @field_validator("new_password_confirm")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class UserResponse(BaseModel):
    """User response schema (public data)"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    email: str
    username: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    bio: Optional[str]
    email_verified: bool
    subscription_tier: str
    monthly_minutes_used: int
    preferred_language: str
    theme: str
    created_at: datetime


class PasswordValidationResponse(BaseModel):
    """Password validation response"""
    is_valid: bool
    errors: List[str]
    strength_score: int
    strength_label: str


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    success: bool = True
