from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from supabase import Client
from datetime import datetime, timezone, timedelta
from app.core.dependencies import get_authed_supabase
from app.core.security import get_current_user
from app.schemas.check_result import CheckResultResponse, CheckResultListResponse, MonitorStats
from app.services import monitor_service
from app.services.export_service import export_results_csv

router = APIRouter(prefix="/monitors/{monitor_id}", tags=["Check Results"])


# Return paginated check results for a monitor within a time window
@router.get("/results", response_model=CheckResultListResponse)
async def get_results(
    monitor_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    hours: int = Query(24, ge=1, le=720),
    user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_authed_supabase),
) -> CheckResultListResponse:
    # Verify ownership
    await monitor_service.get_monitor(supabase, monitor_id, user["id"])
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    offset = (page - 1) * per_page
    response = (
        supabase.table("check_results")
        .select("*", count="exact")
        .eq("monitor_id", monitor_id)
        .gte("timestamp", since)
        .order("timestamp", desc=True)
        .range(offset, offset + per_page - 1)
        .execute()
    )
    return CheckResultListResponse(
        results=[CheckResultResponse(**r) for r in response.data],
        total=response.count or 0,
        page=page,
        per_page=per_page,
    )


# Compute uptime, response time percentiles, and success counts for a monitor
@router.get("/stats", response_model=MonitorStats)
async def get_stats(
    monitor_id: str,
    hours: int = Query(24, ge=1, le=720),
    user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_authed_supabase),
) -> MonitorStats:
    await monitor_service.get_monitor(supabase, monitor_id, user["id"])
    now = datetime.now(timezone.utc)
    since = (now - timedelta(hours=hours)).isoformat()
    response = (
        supabase.table("check_results")
        .select("response_time_ms, success")
        .eq("monitor_id", monitor_id)
        .gte("timestamp", since)
        .order("timestamp", desc=True)
        .execute()
    )
    results = response.data or []
    total = len(results)
    successful = sum(1 for r in results if r["success"])
    failed = total - successful
    response_times = sorted([r["response_time_ms"] for r in results if r["response_time_ms"] is not None])

    # Compute percentiles safely
    avg_rt = sum(response_times) / len(response_times) if response_times else 0.0
    p95_rt = response_times[int(len(response_times) * 0.95)] if response_times else 0.0
    p99_rt = response_times[int(len(response_times) * 0.99)] if response_times else 0.0
    uptime = (successful / total * 100) if total > 0 else 100.0

    return MonitorStats(
        monitor_id=monitor_id,
        uptime_percentage=round(uptime, 2),
        avg_response_time_ms=round(avg_rt, 2),
        p95_response_time_ms=round(p95_rt, 2),
        p99_response_time_ms=round(p99_rt, 2),
        total_checks=total,
        successful_checks=successful,
        failed_checks=failed,
        period_start=datetime.fromisoformat(since),
        period_end=now,
    )


# Export check results as a downloadable CSV file
@router.get("/results/export")
async def export_results(
    monitor_id: str,
    hours: int = Query(24, ge=1, le=720),
    user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_authed_supabase),
) -> PlainTextResponse:
    await monitor_service.get_monitor(supabase, monitor_id, user["id"])
    csv_content = await export_results_csv(supabase, monitor_id, user["id"], hours)
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=results_{monitor_id}.csv"},
    )
