from supabase import Client
from app.schemas.monitor import MonitorCreate, MonitorUpdate, MonitorResponse
from app.core.exceptions import NotFoundError, ForbiddenError


# Fetch a paginated, optionally filtered list of monitors owned by the user
async def list_monitors(
    supabase: Client,
    user_id: str,
    page: int = 1,
    per_page: int = 20,
    is_active: bool | None = None,
    search: str | None = None,
) -> tuple[list[dict], int]:
    query = supabase.table("monitors").select("*", count="exact").eq("user_id", user_id)
    if is_active is not None:
        query = query.eq("is_active", is_active)
    if search:
        query = query.or_(f"name.ilike.%{search}%,url.ilike.%{search}%")
    offset = (page - 1) * per_page
    response = query.order("created_at", desc=True).range(offset, offset + per_page - 1).execute()
    return response.data, response.count or 0


# Fetch a single monitor by ID, scoped to the requesting user
async def get_monitor(supabase: Client, monitor_id: str, user_id: str) -> dict:
    response = (
        supabase.table("monitors")
        .select("*")
        .eq("id", monitor_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not response.data:
        raise NotFoundError("Monitor")
    return response.data


# Insert a new monitor record for the authenticated user
async def create_monitor(supabase: Client, user_id: str, payload: MonitorCreate) -> dict:
    data = payload.model_dump()
    data["user_id"] = user_id
    data["method"] = data["method"].value
    response = supabase.table("monitors").insert(data).execute()
    return response.data[0]


# Partially update an existing monitor after verifying ownership
async def update_monitor(supabase: Client, monitor_id: str, user_id: str, payload: MonitorUpdate) -> dict:
    await get_monitor(supabase, monitor_id, user_id)
    data = payload.model_dump(exclude_none=True)
    if "method" in data:
        data["method"] = data["method"].value
    response = (
        supabase.table("monitors")
        .update(data)
        .eq("id", monitor_id)
        .eq("user_id", user_id)
        .execute()
    )
    return response.data[0]


# Permanently remove a monitor and all its related check results and alert rules
async def delete_monitor(supabase: Client, monitor_id: str, user_id: str) -> None:
    await get_monitor(supabase, monitor_id, user_id)
    supabase.table("monitors").delete().eq("id", monitor_id).eq("user_id", user_id).execute()


# Flip the is_active flag to pause or resume scheduled checks for a monitor
async def toggle_monitor(supabase: Client, monitor_id: str, user_id: str, is_active: bool) -> dict:
    await get_monitor(supabase, monitor_id, user_id)
    response = (
        supabase.table("monitors")
        .update({"is_active": is_active})
        .eq("id", monitor_id)
        .eq("user_id", user_id)
        .execute()
    )
    return response.data[0]
