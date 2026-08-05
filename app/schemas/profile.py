from pydantic import BaseModel, Field
from datetime import datetime


# Full profile response including plan tier and timestamps
class ProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    avatar_url: str
    plan: str
    timezone: str
    created_at: datetime
    updated_at: datetime


# Partial update payload for profile fields the user can change
class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=2048)
    timezone: str | None = Field(default=None, max_length=64)
