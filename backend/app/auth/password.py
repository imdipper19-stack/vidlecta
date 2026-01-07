"""
VideoNotes - Password Validation and Security
"""
import re
from typing import Tuple, List
from passlib.context import CryptContext


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Blacklist of common weak passwords
PASSWORD_BLACKLIST = {
    "password", "password123", "123456", "12345678", "123456789",
    "qwerty", "qwerty123", "abc123", "111111", "123123",
    "admin", "admin123", "letmein", "welcome", "monkey",
    "dragon", "master", "login", "princess", "solo",
    "passw0rd", "football", "baseball", "iloveyou", "trustno1",
    "sunshine", "shadow", "superman", "michael", "password1",
    "пароль", "йцукен", "привет", "любовь", "солнце",
}


class PasswordValidator:
    """
    Strong password validation with detailed requirements.
    
    Requirements:
    - Minimum 8 characters
    - At least 1 uppercase letter (A-Z)
    - At least 1 lowercase letter (a-z)
    - At least 1 digit (0-9)
    - At least 1 special character (!@#$%^&*()_+-=[]{}|;:,.<>?)
    - Not in blacklist
    - No more than 3 consecutive identical characters
    """
    
    MIN_LENGTH = 8
    MAX_LENGTH = 128
    
    SPECIAL_CHARS = r"!@#$%^&*()_+\-=\[\]{}|;:,.<>?/~`"
    
    @classmethod
    def validate(cls, password: str) -> Tuple[bool, List[str]]:
        """
        Validate password strength.
        
        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        errors = []
        
        # Check length
        if len(password) < cls.MIN_LENGTH:
            errors.append(f"Password must be at least {cls.MIN_LENGTH} characters long")
        
        if len(password) > cls.MAX_LENGTH:
            errors.append(f"Password must not exceed {cls.MAX_LENGTH} characters")
        
        # Check uppercase
        if not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter (A-Z)")
        
        # Check lowercase
        if not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter (a-z)")
        
        # Check digit
        if not re.search(r"\d", password):
            errors.append("Password must contain at least one digit (0-9)")
        
        # Check special character
        if not re.search(f"[{re.escape(cls.SPECIAL_CHARS)}]", password):
            errors.append("Password must contain at least one special character (!@#$%^&*)")
        
        # Check blacklist
        if password.lower() in PASSWORD_BLACKLIST:
            errors.append("This password is too common, please choose a stronger one")
        
        # Check consecutive characters (e.g., 'aaaa')
        if re.search(r"(.)\1{3,}", password):
            errors.append("Password must not contain more than 3 consecutive identical characters")
        
        # Check sequential patterns
        sequential_patterns = ["1234", "2345", "3456", "4567", "5678", "6789", "7890",
                              "abcd", "bcde", "cdef", "defg", "efgh", "qwer", "wert", 
                              "asdf", "zxcv", "йцук", "цуке", "фыва"]
        for pattern in sequential_patterns:
            if pattern in password.lower():
                errors.append("Password must not contain sequential patterns like '1234' or 'abcd'")
                break
        
        return (len(errors) == 0, errors)
    
    @classmethod
    def get_strength_score(cls, password: str) -> int:
        """
        Calculate password strength score (0-100).
        
        Returns:
            Integer score from 0 (weak) to 100 (strong)
        """
        score = 0
        
        # Length bonus (up to 30 points)
        score += min(len(password) * 2, 30)
        
        # Character variety (up to 40 points)
        if re.search(r"[a-z]", password):
            score += 10
        if re.search(r"[A-Z]", password):
            score += 10
        if re.search(r"\d", password):
            score += 10
        if re.search(f"[{re.escape(cls.SPECIAL_CHARS)}]", password):
            score += 10
        
        # Bonus for mixed case throughout (up to 10 points)
        upper_count = len(re.findall(r"[A-Z]", password))
        lower_count = len(re.findall(r"[a-z]", password))
        if upper_count > 1 and lower_count > 1:
            score += 10
        
        # Bonus for multiple special chars (up to 10 points)
        special_count = len(re.findall(f"[{re.escape(cls.SPECIAL_CHARS)}]", password))
        if special_count >= 2:
            score += 10
        
        # Penalty for being in blacklist
        if password.lower() in PASSWORD_BLACKLIST:
            score = max(0, score - 50)
        
        # Penalty for consecutive chars
        if re.search(r"(.)\1{2,}", password):
            score = max(0, score - 20)
        
        return min(100, score)
    
    @classmethod
    def get_strength_label(cls, password: str) -> str:
        """
        Get human-readable strength label.
        
        Returns:
            String: 'weak', 'fair', 'good', 'strong', 'excellent'
        """
        score = cls.get_strength_score(password)
        
        if score < 30:
            return "weak"
        elif score < 50:
            return "fair"
        elif score < 70:
            return "good"
        elif score < 90:
            return "strong"
        else:
            return "excellent"


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)
