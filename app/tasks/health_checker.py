from app.services.check_service import run_checks_for_due_monitors
from app.services.alert_service import evaluate_alerts
from app.core.dependencies import get_supabase_admin, get_http_client
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)


# Top-level orchestrator invoked by the internal endpoint when pg_cron fires
async def run_scheduled_checks() -> dict:
    settings = get_settings()
    supabase_admin = get_supabase_admin(settings)
    http_client = await get_http_client()

    # Execute health checks for all monitors whose interval has elapsed
    checks_run = await run_checks_for_due_monitors(
        supabase_admin=supabase_admin,
        http_client=http_client,
        max_concurrent=settings.max_concurrent_checks,
        max_checks_per_run=settings.max_checks_per_run,
    )
    logger.info(f"Completed {checks_run} health checks")

    # Evaluate alert rules against fresh check results and send notifications
    alerts_triggered = await evaluate_alerts(supabase_admin)
    logger.info(f"Triggered {alerts_triggered} alerts")

    return {"checks_run": checks_run, "alerts_triggered": alerts_triggered}
