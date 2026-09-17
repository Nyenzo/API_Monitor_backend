import asyncio
from datetime import datetime, timezone

import httpx
from supabase import Client

from app.core.exceptions import BadRequestError, NotFoundError
from app.schemas.release_verification import ReleaseVerificationCreate
from app.services.check_service import run_single_check


async def run_release_verification(supabase: Client, supabase_admin: Client, http_client: httpx.AsyncClient, user_id: str, payload: ReleaseVerificationCreate) -> dict:
    monitors_response = supabase.table("monitors").select("*").eq("user_id", user_id).in_("id", payload.monitor_ids).execute()
    monitors = monitors_response.data or []
    if len(monitors) != len(payload.monitor_ids):
        raise NotFoundError("Contract monitor")
    if any(monitor.get("monitor_kind") != "contract" for monitor in monitors):
        raise BadRequestError("Release verifications only support contract monitors")

    run = supabase.table("release_verifications").insert({"user_id": user_id, "deployment_ref": payload.deployment_ref, "total_checks": len(monitors)}).execute().data[0]
    semaphore = asyncio.Semaphore(5)

    async def check_monitor(monitor: dict) -> dict:
        async with semaphore:
            return await run_single_check(supabase_admin, http_client, monitor, release_verification_id=run["id"])

    raw_results = await asyncio.gather(*(check_monitor(monitor) for monitor in monitors), return_exceptions=True)
    results = [result for result in raw_results if isinstance(result, dict)]
    passed_checks = sum(1 for result in results if result["success"])
    status = "incomplete" if len(results) != len(monitors) else ("passed" if passed_checks == len(monitors) else "regressed")
    return supabase.table("release_verifications").update({
        "status": status,
        "passed_checks": passed_checks,
        "failed_checks": len(monitors) - passed_checks,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", run["id"]).execute().data[0]


def list_release_verifications(supabase: Client, user_id: str) -> list[dict]:
    return supabase.table("release_verifications").select("*").eq("user_id", user_id).order("started_at", desc=True).limit(50).execute().data or []


def get_release_verification(supabase: Client, run_id: str, user_id: str) -> tuple[dict, list[dict]]:
    response = supabase.table("release_verifications").select("*").eq("id", run_id).eq("user_id", user_id).limit(1).execute()
    run = (response.data or [None])[0]
    if not run:
        raise NotFoundError("Release verification")
    results = supabase.table("check_results").select("*").eq("release_verification_id", run_id).order("timestamp", desc=False).execute().data or []
    return run, results
