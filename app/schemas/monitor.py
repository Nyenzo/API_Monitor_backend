from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from app.models.enums import HttpMethod
import re


# Fields required when creating a new monitor
class MonitorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=8, max_length=2048)
    method: HttpMethod = HttpMethod.GET
    headers: dict[str, str] = Field(default_factory=dict)
    body: str = ""
    interval_seconds: int = Field(default=300, ge=30, le=86400)
    timeout_ms: int = Field(default=10000, ge=1000, le=60000)
    expected_status: int = Field(default=200, ge=100, le=599)
    expected_body_contains: str = ""

    # Ensure the URL starts with http:// or https://
    @field_validator("url")
    @classmethod
    def validate_url_scheme(cls, v: str) -> str:
        if not re.match(r"^https?://", v):
            raise ValueError("URL must start with http:// or https://")
        return v


# Optional fields for partially updating an existing monitor
class MonitorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    url: str | None = Field(default=None, min_length=8, max_length=2048)
    method: HttpMethod | None = None
    headers: dict[str, str] | None = None
    body: str | None = None
    interval_seconds: int | None = Field(default=None, ge=30, le=86400)
    timeout_ms: int | None = Field(default=None, ge=1000, le=60000)
    expected_status: int | None = Field(default=None, ge=100, le=599)
    expected_body_contains: str | None = None
    is_active: bool | None = None

    # Same URL scheme validation applied when a new URL is provided
    @field_validator("url")
    @classmethod
    def validate_url_scheme(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r"^https?://", v):
            raise ValueError("URL must start with http:// or https://")
        return v


# Complete monitor representation returned to the client
class MonitorResponse(BaseModel):
    id: str
    user_id: str
    name: str
    url: str
    method: str
    headers: dict
    body: str
    interval_seconds: int
    timeout_ms: int
    expected_status: int | None
    expected_body_contains: str
    is_active: bool
    last_check_success: bool | None = None
    last_checked_at: datetime | None
    created_at: datetime
    updated_at: datetime


# Paginated list wrapper for the monitors listing endpoint
class MonitorListResponse(BaseModel):
    monitors: list[MonitorResponse]
    total: int
    page: int
    per_page: int


# Payload used by the pause/resume toggle endpoint
class MonitorToggle(BaseModel):
    is_active: bool
