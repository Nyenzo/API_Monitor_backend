import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import HTTPException

from app.core.config import Settings
from app.core.security import get_current_user
from app.core.exceptions import (
    NotFoundError, ForbiddenError, ConflictError,
    BadRequestError, ServiceUnavailableError,
)
from app.models.enums import HttpMethod, AlertType, AlertStatus, PlanTier


class TestSettings:
    def test_cors_origin_list_single(self):
        s = Settings(
            supabase_url="https://test.supabase.co",
            supabase_anon_key="key",
            supabase_service_role_key="key",
            internal_api_key="key",
            cors_origins="http://localhost:3000",
        )
        assert s.cors_origin_list == ["http://localhost:3000"]

    def test_cors_origin_list_multiple(self):
        s = Settings(
            supabase_url="https://test.supabase.co",
            supabase_anon_key="key",
            supabase_service_role_key="key",
            internal_api_key="key",
            cors_origins="http://localhost:3000, https://app.example.com",
        )
        assert len(s.cors_origin_list) == 2
        assert "https://app.example.com" in s.cors_origin_list

    def test_cors_origin_list_empty(self):
        s = Settings(
            supabase_url="https://test.supabase.co",
            supabase_anon_key="key",
            supabase_service_role_key="key",
            internal_api_key="key",
            cors_origins="",
        )
        assert s.cors_origin_list == []

    def test_default_values(self):
        s = Settings(
            supabase_url="https://test.supabase.co",
            supabase_anon_key="key",
            supabase_service_role_key="key",
            internal_api_key="key",
            _env_file=None,
        )
        assert s.rate_limit_per_minute == 60
        assert s.max_concurrent_checks == 200
        assert s.app_version == "1.0.0"
        assert s.debug is False

    def test_debug_release_string_maps_to_false(self):
        s = Settings(
            supabase_url="https://test.supabase.co",
            supabase_anon_key="key",
            supabase_service_role_key="key",
            internal_api_key="key",
            debug="release",
            _env_file=None,
        )
        assert s.debug is False


class TestExceptions:
    def test_not_found_default_message(self):
        err = NotFoundError()
        assert err.status_code == 404
        assert "Resource not found" in err.detail

    def test_not_found_custom_resource(self):
        err = NotFoundError("Monitor")
        assert "Monitor not found" in err.detail

    def test_forbidden_default(self):
        err = ForbiddenError()
        assert err.status_code == 403

    def test_forbidden_custom_message(self):
        err = ForbiddenError("Not your resource")
        assert err.detail == "Not your resource"

    def test_conflict_error(self):
        err = ConflictError()
        assert err.status_code == 409

    def test_bad_request_error(self):
        err = BadRequestError("Invalid input")
        assert err.status_code == 400
        assert err.detail == "Invalid input"

    def test_service_unavailable(self):
        err = ServiceUnavailableError()
        assert err.status_code == 503


class TestEnums:
    def test_all_http_methods(self):
        expected = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
        assert {m.value for m in HttpMethod} == expected

    def test_alert_statuses(self):
        expected = {"triggered", "sent", "failed", "resolved"}
        assert {s.value for s in AlertStatus} == expected

    def test_plan_tiers(self):
        expected = {"free", "pro", "enterprise"}
        assert {t.value for t in PlanTier} == expected


class TestSecurityDependencies:
    async def test_get_current_user_accepts_monitor_api_key(self):
        settings = Settings(
            supabase_url="https://test.supabase.co",
            supabase_anon_key="key",
            supabase_service_role_key="key",
            internal_api_key="key",
            monitor_api_key="monitor-secret",
            _env_file=None,
        )
        supabase = MagicMock()
        supabase.auth.get_user.return_value = MagicMock(
            user=MagicMock(id="monitor-user", email="monitor@example.com")
        )

        with patch(
            "app.core.security.get_monitor_access_token",
            new=AsyncMock(return_value="monitor-token"),
        ):
            user = await get_current_user(
                settings=settings,
                credentials=None,
                x_monitor_api_key="monitor-secret",
                supabase=supabase,
            )

        assert user["id"] == "monitor-user"
        assert user["email"] == "monitor@example.com"
        assert user["token"] == "monitor-token"

    async def test_get_current_user_rejects_invalid_monitor_api_key(self):
        settings = Settings(
            supabase_url="https://test.supabase.co",
            supabase_anon_key="key",
            supabase_service_role_key="key",
            internal_api_key="key",
            monitor_api_key="monitor-secret",
            _env_file=None,
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                settings=settings,
                credentials=None,
                x_monitor_api_key="wrong-secret",
                supabase=MagicMock(),
            )

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid monitor API key."
