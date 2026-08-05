from pydantic import BaseModel, Field
from datetime import datetime
from app.models.enums import AlertType, AlertStatus


# Fields required when creating a new alert rule for a monitor
class AlertRuleCreate(BaseModel):
    alert_type: AlertType
    target: str = Field(min_length=1, max_length=2048)
    threshold_down_minutes: int = Field(default=5, ge=1)
    cooldown_minutes: int = Field(default=30, ge=5)


# Optional fields for partially updating an existing alert rule
class AlertRuleUpdate(BaseModel):
    alert_type: AlertType | None = None
    target: str | None = Field(default=None, min_length=1, max_length=2048)
    threshold_down_minutes: int | None = Field(default=None, ge=1)
    cooldown_minutes: int | None = Field(default=None, ge=5)
    is_active: bool | None = None


# Full alert rule representation returned to the client
class AlertRuleResponse(BaseModel):
    id: str
    monitor_id: str
    alert_type: str
    target: str
    threshold_down_minutes: int
    cooldown_minutes: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# Single alert history entry recording when a notification was sent
class AlertHistoryResponse(BaseModel):
    id: str
    alert_rule_id: str
    triggered_at: datetime
    resolved_at: datetime | None
    status: str
    payload: dict
    created_at: datetime


# Paginated wrapper for alert history listings
class AlertHistoryListResponse(BaseModel):
    history: list[AlertHistoryResponse]
    total: int
    page: int
    per_page: int
