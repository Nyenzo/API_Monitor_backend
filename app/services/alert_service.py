import asyncio
import httpx
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from supabase import Client
from app.core.config import get_settings
from app.core.network_security import validate_public_http_url


# Scan all active alert rules and fire notifications for monitors that have been failing
async def evaluate_alerts(supabase_admin: Client) -> int:
    settings = get_settings()
    # Load all active alert rules with their parent monitor data
    response = (
        supabase_admin.table("alert_rules")
        .select("*, monitors!inner(id, name, url, user_id)")
        .eq("is_active", True)
        .execute()
    )
    rules = response.data or []
    triggered_count = 0

    for rule in rules:
        monitor = rule.get("monitors", {})
        if not monitor:
            continue

        threshold_ago = datetime.now(timezone.utc) - timedelta(minutes=rule["threshold_down_minutes"])

        # Fetch check results within the threshold window for this monitor
        checks_resp = (
            supabase_admin.table("check_results")
            .select("success, timestamp")
            .eq("monitor_id", monitor["id"])
            .gte("timestamp", threshold_ago.isoformat())
            .order("timestamp", desc=True)
            .execute()
        )
        checks = checks_resp.data or []

        if not checks:
            continue

        # Only trigger when every check in the window is a failure
        all_failed = all(not c["success"] for c in checks)
        if not all_failed:
            continue

        # Enforce cooldown period to avoid spamming the same alert
        cooldown_ago = datetime.now(timezone.utc) - timedelta(minutes=rule["cooldown_minutes"])
        recent_alert_resp = (
            supabase_admin.table("alert_history")
            .select("id, triggered_at")
            .eq("alert_rule_id", rule["id"])
            .gte("triggered_at", cooldown_ago.isoformat())
            .limit(1)
            .execute()
        )
        if recent_alert_resp.data:
            continue

        # Assemble the alert payload with monitor context
        payload = {
            "monitor_name": monitor["name"],
            "monitor_url": monitor["url"],
            "alert_type": rule["alert_type"],
            "target": rule["target"],
            "failure_count": len(checks),
            "threshold_minutes": rule["threshold_down_minutes"],
            "triggered_at": datetime.now(timezone.utc).isoformat(),
        }

        # Persist the alert record before attempting delivery
        supabase_admin.table("alert_history").insert({
            "alert_rule_id": rule["id"],
            "status": "triggered",
            "payload": payload,
        }).execute()

        # Dispatch the notification via the configured channel
        try:
            if rule["alert_type"] == "email":
                await send_email_alert(settings, rule["target"], payload)
            elif rule["alert_type"] == "slack":
                await send_slack_alert(rule["target"], payload)
            elif rule["alert_type"] == "webhook":
                await send_webhook_alert(rule["target"], payload)

            # Mark the alert as successfully sent
            supabase_admin.table("alert_history").update(
                {"status": "sent"}
            ).eq("alert_rule_id", rule["id"]).order("triggered_at", desc=True).limit(1).execute()
        except (httpx.HTTPError, smtplib.SMTPException, OSError):
            # Mark the alert as failed if delivery throws
            supabase_admin.table("alert_history").update(
                {"status": "failed"}
            ).eq("alert_rule_id", rule["id"]).order("triggered_at", desc=True).limit(1).execute()

        triggered_count += 1

    return triggered_count


# Deliver an alert email via SMTP with monitor failure details
async def send_email_alert(settings, target: str, payload: dict) -> None:
    if not settings.smtp_host:
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[API Monitor] {payload['monitor_name']} is DOWN"
    msg["From"] = settings.smtp_from_email
    msg["To"] = target
    body = (
        f"Monitor: {payload['monitor_name']}\n"
        f"URL: {payload['monitor_url']}\n"
        f"Status: DOWN for {payload['threshold_minutes']} minutes\n"
        f"Failed checks: {payload['failure_count']}\n"
        f"Time: {payload['triggered_at']}\n"
    )
    msg.attach(MIMEText(body, "plain"))
    def deliver() -> None:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.smtp_from_email, target, msg.as_string())

    await asyncio.to_thread(deliver)


# Send a Slack message via incoming webhook with formatted alert blocks
async def send_slack_alert(webhook_url: str, payload: dict) -> None:
    await validate_public_http_url(webhook_url)
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(webhook_url, json={
            "text": f":rotating_light: *{payload['monitor_name']}* is DOWN",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*Monitor:* {payload['monitor_name']}\n"
                            f"*URL:* {payload['monitor_url']}\n"
                            f"*Down for:* {payload['threshold_minutes']} minutes\n"
                            f"*Failed checks:* {payload['failure_count']}"
                        ),
                    },
                }
            ],
        })
        response.raise_for_status()


# POST the raw alert payload to an arbitrary webhook URL
async def send_webhook_alert(webhook_url: str, payload: dict) -> None:
    await validate_public_http_url(webhook_url)
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(webhook_url, json=payload)
        response.raise_for_status()
