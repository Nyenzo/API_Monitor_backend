import csv
import io
from supabase import Client


# Build a CSV string from check results for a given monitor within the specified time range
async def export_results_csv(
    supabase: Client,
    monitor_id: str,
    user_id: str,
    hours: int = 24,
) -> str:
    from datetime import datetime, timezone, timedelta
    # Compute the earliest timestamp to include in the export
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    response = (
        supabase.table("check_results")
        .select("timestamp, status_code, response_time_ms, success, response_size_bytes, error_message")
        .eq("monitor_id", monitor_id)
        .gte("timestamp", since)
        .order("timestamp", desc=True)
        .execute()
    )
    rows = response.data or []

    # Write the rows into an in-memory CSV buffer
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["timestamp", "status_code", "response_time_ms", "success", "response_size_bytes", "error_message"],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()
