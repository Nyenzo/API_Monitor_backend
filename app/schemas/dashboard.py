from pydantic import BaseModel
from app.schemas.alert import AlertHistoryResponse


# Aggregated dashboard data returned by the summary endpoint
class DashboardSummary(BaseModel):
    total_monitors: int
    active_monitors: int
    monitors_up: int
    monitors_down: int
    avg_response_time_ms: float
    overall_uptime_percentage: float
    recent_alerts: list[AlertHistoryResponse]
    checks_last_24h: int
