from unittest.mock import MagicMock

import pytest

from app.schemas.release_verification import ReleaseVerificationCreate
from app.services.release_verification_service import run_release_verification


def make_supabase(monitors: list[dict], completed_run: dict) -> MagicMock:
    supabase = MagicMock()
    monitor_query = MagicMock()
    monitor_query.select.return_value = monitor_query
    monitor_query.eq.return_value = monitor_query
    monitor_query.in_.return_value = monitor_query
    monitor_query.execute.return_value.data = monitors

    release_query = MagicMock()
    release_query.insert.return_value.execute.return_value.data = [{"id": "run-1"}]
    release_query.update.return_value.eq.return_value.execute.return_value.data = [completed_run]

    supabase.table.side_effect = lambda name: monitor_query if name == "monitors" else release_query
    return supabase


class TestReleaseVerificationService:
    async def test_marks_a_run_passed_when_all_contract_checks_pass(self, monkeypatch):
        monitors = [
            {"id": "contract-1", "monitor_kind": "contract"},
            {"id": "contract-2", "monitor_kind": "contract"},
        ]
        completed_run = {
            "id": "run-1", "user_id": "user-1", "deployment_ref": "sha-123",
            "status": "passed", "total_checks": 2, "passed_checks": 2,
            "failed_checks": 0, "started_at": "2026-01-01T00:00:00Z",
            "completed_at": "2026-01-01T00:00:01Z",
        }

        async def passing_check(*_args, **_kwargs):
            return {"success": True}

        monkeypatch.setattr("app.services.release_verification_service.run_single_check", passing_check)
        result = await run_release_verification(
            make_supabase(monitors, completed_run), MagicMock(), MagicMock(), "user-1",
            ReleaseVerificationCreate(deployment_ref="sha-123", monitor_ids=["contract-1", "contract-2"]),
        )

        assert result["status"] == "passed"

    async def test_marks_a_run_regressed_when_a_contract_check_fails(self, monkeypatch):
        monitors = [{"id": "contract-1", "monitor_kind": "contract"}]
        completed_run = {
            "id": "run-1", "user_id": "user-1", "deployment_ref": "sha-124",
            "status": "regressed", "total_checks": 1, "passed_checks": 0,
            "failed_checks": 1, "started_at": "2026-01-01T00:00:00Z",
            "completed_at": "2026-01-01T00:00:01Z",
        }

        async def failing_check(*_args, **_kwargs):
            return {"success": False}

        monkeypatch.setattr("app.services.release_verification_service.run_single_check", failing_check)
        result = await run_release_verification(
            make_supabase(monitors, completed_run), MagicMock(), MagicMock(), "user-1",
            ReleaseVerificationCreate(deployment_ref="sha-124", monitor_ids=["contract-1"]),
        )

        assert result["status"] == "regressed"
