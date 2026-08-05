from fastapi import APIRouter, Depends
from supabase import Client
from datetime import datetime, timezone, timedelta
from app.core.dependencies import get_authed_supabase
from app.core.security import get_current_user
from app.schemas.dashboard import DashboardSummary
from app.schemas.alert import AlertHistoryResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# Aggregate dashboard stats: monitor counts, uptime, avg latency, and recent alerts
@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_authed_supabase),
) -> DashboardSummary:
    # Fetch all monitors for this user
    monitors_resp = (
        supabase.table("monitors")
        .select("id, is_active")
        .eq("user_id", user["id"])
        .execute()
    )
    monitors = monitors_resp.data or []
    monitor_ids = [m["id"] for m in monitors]
    total = len(monitors)
    active = sum(1 for m in monitors if m["is_active"])

    if not monitor_ids:
        return DashboardSummary(
            total_monitors=0, active_monitors=0, monitors_up=0, monitors_down=0,
            avg_response_time_ms=0, overall_uptime_percentage=100,
            recent_alerts=[], checks_last_24h=0,
        )

    # Get latest check result per monitor to determine up/down status
    up_count = 0
    down_count = 0
    all_response_times: list[int] = []
    all_successes: list[bool] = []
    since_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

    for mid in monitor_ids:
        latest = (
            supabase.table("check_results")
            .select("success, response_time_ms")
            .eq("monitor_id", mid)
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )
        if latest.data:
            if latest.data[0]["success"]:
                up_count += 1
            else:
                down_count += 1

    # 24h aggregate stats
    checks_24h_resp = (
        supabase.table("check_results")
        .select("success, response_time_ms", count="exact")
        .in_("monitor_id", monitor_ids)
        .gte("timestamp", since_24h)
        .execute()
    )
    checks_24h_data = checks_24h_resp.data or []
    checks_last_24h = checks_24h_resp.count or 0
    for c in checks_24h_data:
        all_successes.append(c["success"])
        if c["response_time_ms"] is not None:
            all_response_times.append(c["response_time_ms"])

    avg_rt = sum(all_response_times) / len(all_response_times) if all_response_times else 0.0
    uptime = (sum(1 for s in all_successes if s) / len(all_successes) * 100) if all_successes else 100.0

    # Recent alerts
    alerts_resp = (
        supabase.table("alert_history")
        .select("*, alert_rules!inner(monitor_id, monitors!inner(user_id))")
        .order("triggered_at", desc=True)
        .limit(10)
        .execute()
    )

    return DashboardSummary(
        total_monitors=total,
        active_monitors=active,
        monitors_up=up_count,
        monitors_down=down_count,
        avg_response_time_ms=round(avg_rt, 2),
        overall_uptime_percentage=round(uptime, 2),
        recent_alerts=[AlertHistoryResponse(**a) for a in (alerts_resp.data or [])],
        checks_last_24h=checks_last_24h,
    )
