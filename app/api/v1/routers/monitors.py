from fastapi import APIRouter, Depends, Query
from supabase import Client
from app.core.dependencies import get_authed_supabase, get_supabase_admin, get_http_client
from app.core.security import get_current_user
from app.schemas.monitor import (
    MonitorCreate, MonitorUpdate, MonitorResponse,
    MonitorListResponse, MonitorToggle,
)
from app.services import monitor_service
from app.services.check_service import run_single_check
import httpx

router = APIRouter(prefix="/monitors", tags=["Monitors"])


# List all monitors for the current user with optional filtering and search
@router.get("", response_model=MonitorListResponse)
async def list_monitors(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    is_active: bool | None = None,
    search: str | None = None,
    user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_authed_supabase),
) -> MonitorListResponse:
    monitors, total = await monitor_service.list_monitors(
        supabase, user["id"], page, per_page, is_active, search,
    )
    return MonitorListResponse(
        monitors=[MonitorResponse(**m) for m in monitors],
        total=total,
        page=page,
        per_page=per_page,
    )


# Create a new monitor under the authenticated user's account
@router.post("", response_model=MonitorResponse, status_code=201)
async def create_monitor(
    payload: MonitorCreate,
    user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_authed_supabase),
) -> MonitorResponse:
    data = await monitor_service.create_monitor(supabase, user["id"], payload)
    return MonitorResponse(**data)


# Fetch a single monitor by its UUID
@router.get("/{monitor_id}", response_model=MonitorResponse)
async def get_monitor(
    monitor_id: str,
    user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_authed_supabase),
) -> MonitorResponse:
    data = await monitor_service.get_monitor(supabase, monitor_id, user["id"])
    return MonitorResponse(**data)


# Apply a partial update to an existing monitor's configuration
@router.patch("/{monitor_id}", response_model=MonitorResponse)
async def update_monitor(
    monitor_id: str,
    payload: MonitorUpdate,
    user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_authed_supabase),
) -> MonitorResponse:
    data = await monitor_service.update_monitor(supabase, monitor_id, user["id"], payload)
    return MonitorResponse(**data)


# Permanently delete a monitor and cascade-remove its results and rules
@router.delete("/{monitor_id}", status_code=204)
async def delete_monitor(
    monitor_id: str,
    user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_authed_supabase),
) -> None:
    await monitor_service.delete_monitor(supabase, monitor_id, user["id"])


# Run an immediate one-off health check and return the result
@router.post("/{monitor_id}/test")
async def test_monitor(
    monitor_id: str,
    user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_authed_supabase),
    supabase_admin: Client = Depends(get_supabase_admin),
    http_client: httpx.AsyncClient = Depends(get_http_client),
) -> dict:
    monitor = await monitor_service.get_monitor(supabase, monitor_id, user["id"])
    result = await run_single_check(supabase_admin, http_client, monitor)
    return result


# Pause or resume scheduled checks for a monitor
@router.patch("/{monitor_id}/toggle", response_model=MonitorResponse)
async def toggle_monitor(
    monitor_id: str,
    payload: MonitorToggle,
    user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_authed_supabase),
) -> MonitorResponse:
    data = await monitor_service.toggle_monitor(supabase, monitor_id, user["id"], payload.is_active)
    return MonitorResponse(**data)
