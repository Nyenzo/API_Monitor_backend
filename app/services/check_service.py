import asyncio
import time
import httpx
from supabase import Client
from datetime import datetime, timezone
from app.core.network_security import validate_public_http_url


# Perform a single HTTP request against a monitor's URL and record the outcome
async def execute_single_check(
    http_client: httpx.AsyncClient,
    monitor: dict,
) -> dict:
    start = time.perf_counter()
    # Initialize the result dict with default failure values
    result = {
        "monitor_id": monitor["id"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status_code": None,
        "response_time_ms": None,
        "success": False,
        "response_size_bytes": 0,
        "error_message": "",
        "response_snippet": "",
    }
    try:
        await validate_public_http_url(monitor["url"])
        # Build the request from the monitor's configuration
        timeout = httpx.Timeout(monitor.get("timeout_ms", 10000) / 1000.0)
        headers = monitor.get("headers", {}) or {}
        body = monitor.get("body", "") or None
        response = await http_client.request(
            method=monitor["method"],
            url=monitor["url"],
            headers=headers,
            content=body if monitor["method"] in ("POST", "PUT", "PATCH") else None,
            timeout=timeout,
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        body_text = response.text[:500] if response.text else ""
        result["status_code"] = response.status_code
        result["response_time_ms"] = elapsed_ms
        result["response_size_bytes"] = len(response.content)
        result["response_snippet"] = body_text[:200]

        # Determine success based on expected status code and body content
        status_ok = True
        if monitor.get("expected_status"):
            status_ok = response.status_code == monitor["expected_status"]
        body_ok = True
        if monitor.get("expected_body_contains"):
            body_ok = monitor["expected_body_contains"] in body_text
        result["success"] = status_ok and body_ok
        if not status_ok:
            result["error_message"] = f"Expected status {monitor['expected_status']}, got {response.status_code}"
        elif not body_ok:
            result["error_message"] = "Response body missing expected content"
    except ValueError as exc:
        result["error_message"] = str(exc)
    except httpx.TimeoutException:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        result["response_time_ms"] = elapsed_ms
        result["error_message"] = "Request timed out"
    except httpx.ConnectError:
        result["error_message"] = "Connection refused or DNS resolution failed"
    except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
        result["error_message"] = f"Unexpected error: {str(exc)[:200]}"
    return result


# Find all active monitors due for a check and run them concurrently
async def run_checks_for_due_monitors(
    supabase_admin: Client,
    http_client: httpx.AsyncClient,
    max_concurrent: int = 200,
    max_checks_per_run: int = 500,
) -> int:
    # Lease monitors in PostgreSQL so concurrent workers cannot check the same target.
    response = supabase_admin.rpc(
        "get_due_monitors",
        {"batch_size": max_checks_per_run},
    ).execute()
    monitors = response.data if response.data else []
    if not monitors:
        response = (
            supabase_admin.table("monitors")
            .select("*")
            .eq("is_active", True)
            .execute()
        )
        monitors = response.data or []
        now = datetime.now(timezone.utc)
        # Filter to monitors whose interval has elapsed since their last check
        monitors = [
            m for m in monitors
            if not m.get("last_checked_at")
            or (now - datetime.fromisoformat(m["last_checked_at"].replace("Z", "+00:00"))).total_seconds()
            >= m["interval_seconds"]
        ]

    if not monitors:
        return 0

    # Use a semaphore to cap the number of in-flight HTTP requests
    semaphore = asyncio.Semaphore(max_concurrent)

    async def bounded_check(monitor: dict) -> dict:
        async with semaphore:
            return await execute_single_check(http_client, monitor)

    results = await asyncio.gather(*[bounded_check(m) for m in monitors], return_exceptions=True)

    # Insert all successful check results in a single batch
    valid_results = [r for r in results if isinstance(r, dict)]
    if valid_results:
        supabase_admin.table("check_results").insert(valid_results).execute()

    # Update each monitor's last_checked_at and last_check_success
    for r in valid_results:
        supabase_admin.table("monitors").update({
            "last_checked_at": datetime.now(timezone.utc).isoformat(),
            "last_check_success": r["success"],
            "check_lease_until": None,
        }).eq("id", r["monitor_id"]).execute()

    return len(valid_results)


# Execute a single immediate check for a specific monitor and persist the result
async def run_single_check(
    supabase_admin: Client,
    http_client: httpx.AsyncClient,
    monitor: dict,
) -> dict:
    result = await execute_single_check(http_client, monitor)
    supabase_admin.table("check_results").insert(result).execute()
    supabase_admin.table("monitors").update({
        "last_checked_at": datetime.now(timezone.utc).isoformat(),
        "last_check_success": result["success"],
        "check_lease_until": None,
    }).eq("id", monitor["id"]).execute()
    return result
