from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class AuthCredentials(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or "." not in normalized.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address")
        return normalized


class RegisterRequest(AuthCredentials):
    pass


class AuthUserResponse(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool
    created_at: datetime


class AuthResponse(BaseModel):
    user: AuthUserResponse
    message: str
