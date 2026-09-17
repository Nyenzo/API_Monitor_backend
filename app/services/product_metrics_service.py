import logging
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone

from supabase import Client

OPENAPI_PREVIEWED = "openapi_previewed"
QUERY_LIMIT = 10_000
logger = logging.getLogger(__name__)


def record_openapi_preview(supabase: Client, user_id: str) -> None:
    try:
        supabase.table("product_events").insert({"user_id": user_id, "event_type": OPENAPI_PREVIEWED}).execute()
    except Exception:
        # Analytics must never make a valid customer import fail.
        logger.warning("Could not record product activation event")


def summarize_activation(
    events: Iterable[dict],
    contract_monitors: Iterable[dict],
    release_runs: Iterable[dict],
    window_start: datetime,
) -> dict:
    imported_at: dict[str, datetime] = {}
    for event in events:
        if event.get("event_type") != OPENAPI_PREVIEWED:
            continue
        created_at = _parse_timestamp(event["created_at"])
        if created_at < window_start:
            continue
        user_id = event["user_id"]
        imported_at[user_id] = min(imported_at.get(user_id, created_at), created_at)

    monitor_counts = {user_id: 0 for user_id in imported_at}
    for monitor in contract_monitors:
        user_id = monitor.get("user_id")
        if user_id in imported_at and _parse_timestamp(monitor["created_at"]) >= imported_at[user_id]:
            monitor_counts[user_id] += 1

    runs_by_user = {user_id: [] for user_id in imported_at}
    for run in release_runs:
        user_id = run.get("user_id")
        if user_id in imported_at:
            started_at = _parse_timestamp(run["started_at"])
            if started_at >= imported_at[user_id]:
                runs_by_user[user_id].append(started_at)

    for runs in runs_by_user.values():
        runs.sort()
    return {
        "imported_spec_users": len(imported_at),
        "two_contract_monitor_users": sum(count >= 2 for count in monitor_counts.values()),
        "first_verification_users": sum(bool(runs) for runs in runs_by_user.values()),
        "second_verification_within_14_days_users": sum(
            len(runs) >= 2 and runs[1] - runs[0] <= timedelta(days=14)
            for runs in runs_by_user.values()
        ),
    }


def get_activation_metrics(supabase_admin: Client, since_days: int = 90) -> dict:
    window_start = datetime.now(timezone.utc) - timedelta(days=since_days)
    since = window_start.isoformat()
    events = supabase_admin.table("product_events").select("user_id,event_type,created_at").eq("event_type", OPENAPI_PREVIEWED).gte("created_at", since).order("created_at").limit(QUERY_LIMIT).execute().data or []
    monitors = supabase_admin.table("monitors").select("user_id,created_at").eq("monitor_kind", "contract").gte("created_at", since).limit(QUERY_LIMIT).execute().data or []
    runs = supabase_admin.table("release_verifications").select("user_id,started_at").gte("started_at", since).limit(QUERY_LIMIT).execute().data or []
    return {"window_start": window_start, **summarize_activation(events, monitors, runs, window_start)}


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
