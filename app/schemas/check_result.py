from pydantic import BaseModel
from datetime import datetime


# Single health-check result returned to the client
class CheckResultResponse(BaseModel):
    id: str
    monitor_id: str
    timestamp: datetime
    status_code: int | None
    response_time_ms: int | None
    success: bool
    response_size_bytes: int
    error_message: str
    response_snippet: str
    created_at: datetime


# Paginated wrapper for check result listings
class CheckResultListResponse(BaseModel):
    results: list[CheckResultResponse]
    total: int
    page: int
    per_page: int


# Aggregated uptime and latency statistics for a given time window
class MonitorStats(BaseModel):
    monitor_id: str
    uptime_percentage: float
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    total_checks: int
    successful_checks: int
    failed_checks: int
    period_start: datetime
    period_end: datetime
