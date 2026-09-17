from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.check_result import CheckResultResponse


class ReleaseVerificationCreate(BaseModel):
    deployment_ref: str = Field(min_length=1, max_length=255)
    monitor_ids: list[str] = Field(min_length=1, max_length=25)

    @field_validator("monitor_ids")
    @classmethod
    def require_unique_monitor_ids(cls, monitor_ids: list[str]) -> list[str]:
        if len(set(monitor_ids)) != len(monitor_ids):
            raise ValueError("Each monitor can only be checked once per release verification")
        return monitor_ids


class ReleaseVerificationResponse(BaseModel):
    id: str
    user_id: str
    deployment_ref: str
    status: str
    total_checks: int
    passed_checks: int
    failed_checks: int
    started_at: datetime
    completed_at: datetime | None


class ReleaseVerificationDetail(ReleaseVerificationResponse):
    results: list[CheckResultResponse]
