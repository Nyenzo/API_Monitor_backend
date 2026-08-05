from fastapi import APIRouter, Depends, Query
from supabase import Client
from app.core.dependencies import get_authed_supabase
from app.core.security import get_current_user
from app.core.exceptions import NotFoundError
from app.schemas.alert import (
    AlertRuleCreate, AlertRuleUpdate, AlertRuleResponse,
    AlertHistoryResponse, AlertHistoryListResponse,
)
from app.services import monitor_service

router = APIRouter(tags=["Alerts"])


# List all alert rules configured for a specific monitor
@router.get("/monitors/{monitor_id}/alerts", response_model=list[AlertRuleResponse])
async def list_alert_rules(
    monitor_id: str,
    user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_authed_supabase),
) -> list[AlertRuleResponse]:
    await monitor_service.get_monitor(supabase, monitor_id, user["id"])
    response = (
        supabase.table("alert_rules")
        .select("*")
        .eq("monitor_id", monitor_id)
        .order("created_at", desc=True)
        .execute()
    )
    return [AlertRuleResponse(**r) for r in response.data]


# Create a new alert rule for a monitor with the given threshold and type
@router.post("/monitors/{monitor_id}/alerts", response_model=AlertRuleResponse, status_code=201)
async def create_alert_rule(
    monitor_id: str,
    payload: AlertRuleCreate,
    user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_authed_supabase),
) -> AlertRuleResponse:
    await monitor_service.get_monitor(supabase, monitor_id, user["id"])
    data = payload.model_dump()
    data["monitor_id"] = monitor_id
    data["alert_type"] = data["alert_type"].value
    response = supabase.table("alert_rules").insert(data).execute()
    return AlertRuleResponse(**response.data[0])


# Update an existing alert rule, relying on RLS for ownership enforcement
@router.patch("/alerts/{alert_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    alert_id: str,
    payload: AlertRuleUpdate,
    user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_authed_supabase),
) -> AlertRuleResponse:
    # RLS ensures the user can only update their own rules
    data = payload.model_dump(exclude_none=True)
    if "alert_type" in data:
        data["alert_type"] = data["alert_type"].value
    response = (
        supabase.table("alert_rules")
        .update(data)
        .eq("id", alert_id)
        .execute()
    )
    if not response.data:
        raise NotFoundError("Alert rule")
    return AlertRuleResponse(**response.data[0])


# Delete an alert rule by id, returns 404 if not found
@router.delete("/alerts/{alert_id}", status_code=204)
async def delete_alert_rule(
    alert_id: str,
    user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_authed_supabase),
) -> None:
    response = (
        supabase.table("alert_rules")
        .delete()
        .eq("id", alert_id)
        .execute()
    )
    if not response.data:
        raise NotFoundError("Alert rule")


# List all alert rules across every monitor owned by the current user
@router.get("/alerts/rules", response_model=list[AlertRuleResponse])
async def list_all_alert_rules(
    user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_authed_supabase),
) -> list[AlertRuleResponse]:
    monitors_resp = (
        supabase.table("monitors")
        .select("id")
        .eq("user_id", user["id"])
        .execute()
    )
    monitor_ids = [m["id"] for m in monitors_resp.data]
    if not monitor_ids:
        return []
    response = (
        supabase.table("alert_rules")
        .select("*")
        .in_("monitor_id", monitor_ids)
        .order("created_at", desc=True)
        .execute()
    )
    return [AlertRuleResponse(**r) for r in response.data]


# Retrieve paginated alert history for a specific alert rule
@router.get("/alerts/{alert_id}/history", response_model=AlertHistoryListResponse)
async def get_alert_history(
    alert_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_authed_supabase),
) -> AlertHistoryListResponse:
    offset = (page - 1) * per_page
    response = (
        supabase.table("alert_history")
        .select("*", count="exact")
        .eq("alert_rule_id", alert_id)
        .order("triggered_at", desc=True)
        .range(offset, offset + per_page - 1)
        .execute()
    )
    return AlertHistoryListResponse(
        history=[AlertHistoryResponse(**r) for r in response.data],
        total=response.count or 0,
        page=page,
        per_page=per_page,
    )


# Retrieve paginated alert history across all monitors owned by the current user
@router.get("/alerts/history", response_model=AlertHistoryListResponse)
async def get_all_alert_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_authed_supabase),
) -> AlertHistoryListResponse:
    # Get all alert history for the current user via joined query
    offset = (page - 1) * per_page
    response = (
        supabase.table("alert_history")
        .select("*, alert_rules!inner(monitor_id, monitors!inner(user_id))", count="exact")
        .order("triggered_at", desc=True)
        .range(offset, offset + per_page - 1)
        .execute()
    )
    return AlertHistoryListResponse(
        history=[AlertHistoryResponse(**r) for r in response.data],
        total=response.count or 0,
        page=page,
        per_page=per_page,
    )
