from datetime import datetime, timezone

from app.services.product_metrics_service import summarize_activation


class TestActivationSummary:
    def test_counts_each_activation_stage_for_imported_users(self):
        window_start = datetime(2026, 9, 1, tzinfo=timezone.utc)
        events = [
            {"user_id": "user-1", "event_type": "openapi_previewed", "created_at": "2026-09-02T09:00:00Z"},
            {"user_id": "user-2", "event_type": "openapi_previewed", "created_at": "2026-09-03T09:00:00Z"},
        ]
        monitors = [
            {"user_id": "user-1", "created_at": "2026-09-02T10:00:00Z"},
            {"user_id": "user-1", "created_at": "2026-09-02T10:01:00Z"},
            {"user_id": "user-2", "created_at": "2026-09-03T10:00:00Z"},
        ]
        runs = [
            {"user_id": "user-1", "started_at": "2026-09-03T09:00:00Z"},
            {"user_id": "user-1", "started_at": "2026-09-10T09:00:00Z"},
            {"user_id": "user-2", "started_at": "2026-09-20T09:00:00Z"},
        ]

        summary = summarize_activation(events, monitors, runs, window_start)

        assert summary == {
            "imported_spec_users": 2,
            "two_contract_monitor_users": 1,
            "first_verification_users": 2,
            "second_verification_within_14_days_users": 1,
        }
