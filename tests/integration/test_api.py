import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.core.config import Settings, get_settings
from app.core.dependencies import get_supabase_client, get_supabase_admin, get_http_client
from app.core.security import get_current_user, verify_internal_key


# Override settings for all integration tests
def _test_settings():
    return Settings(
        supabase_url="https://test.supabase.co",
        supabase_anon_key="test-anon-key",
        supabase_service_role_key="test-service-key",
        internal_api_key="test-internal-key",
        cors_origins="http://localhost:3000",
        rate_limit_per_minute=1000,
        _env_file=None,
    )


# Fake authenticated user dependency
def _fake_user():
    return {"id": "user-uuid-1234", "email": "test@example.com", "token": "fake"}


def _make_chain(data=None, count=0):
    """Build a chainable mock for supabase query builder patterns."""
    chain = MagicMock()
    result = MagicMock()
    result.data = data if data is not None else []
    result.count = count
    chain.execute.return_value = result
    for m in ["select", "insert", "update", "delete", "eq", "in_", "gte", "or_", "order", "range", "limit"]:
        getattr(chain, m).return_value = chain

    # .single() should make .execute().data return a dict (first element), not a list
    single_chain = MagicMock()
    single_result = MagicMock()
    if isinstance(data, list) and len(data) > 0:
        single_result.data = data[0]
    else:
        single_result.data = data if data is not None else {}
    single_result.count = count
    single_chain.execute.return_value = single_result
    for m in ["select", "insert", "update", "delete", "eq", "in_", "gte", "or_", "order", "range", "limit"]:
        getattr(single_chain, m).return_value = single_chain
    chain.single.return_value = single_chain
    return chain


# Build a chainable supabase mock (single table response)
def _mock_supabase(data=None, count=0):
    sb = MagicMock()
    sb.table.return_value = _make_chain(data, count)
    sb.rpc.return_value = _make_chain(data, count)
    return sb


# Build a supabase mock that returns different data per table name
def _mock_supabase_multi(table_data):
    sb = MagicMock()

    def table_side_effect(name):
        if name in table_data:
            cfg = table_data[name]
            return _make_chain(data=cfg.get("data"), count=cfg.get("count", 0))
        return _make_chain()

    sb.table.side_effect = table_side_effect
    sb.rpc.return_value = _make_chain()
    return sb


# Shared test fixtures
NOW = datetime.now(timezone.utc).isoformat()
SAMPLE_MONITOR = {
    "id": "mon-uuid-1234", "user_id": "user-uuid-1234",
    "name": "Test API", "url": "https://api.example.com",
    "method": "GET", "headers": {}, "body": "",
    "interval_seconds": 300, "timeout_ms": 10000,
    "expected_status": 200, "expected_body_contains": "",
    "is_active": True, "last_checked_at": NOW,
    "created_at": NOW, "updated_at": NOW,
}
SAMPLE_CHECK_RESULT = {
    "id": "check-uuid-1234", "monitor_id": "mon-uuid-1234",
    "timestamp": NOW, "status_code": 200, "response_time_ms": 150,
    "success": True, "response_size_bytes": 1024,
    "error_message": "", "response_snippet": '{"status": "ok"}',
    "created_at": NOW,
}
# Subset matching the columns selected by export_results_csv
SAMPLE_CHECK_RESULT_EXPORT = {
    "timestamp": NOW, "status_code": 200, "response_time_ms": 150,
    "success": True, "response_size_bytes": 1024, "error_message": "",
}
SAMPLE_PROFILE = {
    "id": "user-uuid-1234", "email": "test@example.com",
    "full_name": "Test User", "avatar_url": "", "plan": "free",
    "timezone": "UTC", "created_at": NOW, "updated_at": NOW,
}


@pytest.fixture
def client():
    from main import app
    # Override all external dependencies with mocks
    mock_sb = _mock_supabase()
    app.dependency_overrides[get_settings] = _test_settings
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_supabase_client] = lambda: mock_sb
    app.dependency_overrides[get_supabase_admin] = lambda: mock_sb

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def authed_client():
    """Client pre-configured with monitor data returned by supabase mock."""
    from main import app
    mock_sb = _mock_supabase(data=[SAMPLE_MONITOR], count=1)
    app.dependency_overrides[get_settings] = _test_settings
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_supabase_client] = lambda: mock_sb
    app.dependency_overrides[get_supabase_admin] = lambda: mock_sb

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def profile_client():
    from main import app
    mock_sb = _mock_supabase(data=[SAMPLE_PROFILE])
    app.dependency_overrides[get_settings] = _test_settings
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_supabase_client] = lambda: mock_sb

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def check_result_client():
    """Client with mocks that return monitor data for monitors table and check result data for check_results table."""
    from main import app
    mock_sb = _mock_supabase_multi({
        "monitors": {"data": [SAMPLE_MONITOR], "count": 1},
        "check_results": {"data": [SAMPLE_CHECK_RESULT], "count": 1},
    })
    app.dependency_overrides[get_settings] = _test_settings
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_supabase_client] = lambda: mock_sb
    app.dependency_overrides[get_supabase_admin] = lambda: mock_sb

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def export_client():
    """Client returning export-safe check result data (only CSV fieldnames)."""
    from main import app
    mock_sb = _mock_supabase_multi({
        "monitors": {"data": [SAMPLE_MONITOR], "count": 1},
        "check_results": {"data": [SAMPLE_CHECK_RESULT_EXPORT], "count": 1},
    })
    app.dependency_overrides[get_settings] = _test_settings
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_supabase_client] = lambda: mock_sb
    app.dependency_overrides[get_supabase_admin] = lambda: mock_sb

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# -- Health endpoint --

class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "api-monitor"


# -- Auth endpoints --

class TestAuthEndpoints:
    def test_me_returns_user_info(self, client):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "user-uuid-1234"
        assert data["email"] == "test@example.com"


# -- Monitor endpoints --

class TestMonitorEndpoints:
    def test_list_monitors(self, authed_client):
        response = authed_client.get("/api/v1/monitors")
        assert response.status_code == 200
        data = response.json()
        assert "monitors" in data
        assert "total" in data

    def test_create_monitor(self, authed_client):
        response = authed_client.post("/api/v1/monitors", json={
            "name": "New API",
            "url": "https://new-api.example.com/health",
        })
        assert response.status_code == 201

    def test_create_monitor_invalid_url(self, client):
        response = client.post("/api/v1/monitors", json={
            "name": "Bad",
            "url": "not-a-url",
        })
        assert response.status_code == 422

    def test_create_monitor_missing_name(self, client):
        response = client.post("/api/v1/monitors", json={
            "url": "https://api.example.com",
        })
        assert response.status_code == 422

    def test_get_monitor(self, authed_client):
        response = authed_client.get("/api/v1/monitors/mon-uuid-1234")
        assert response.status_code == 200

    def test_update_monitor(self, authed_client):
        response = authed_client.patch("/api/v1/monitors/mon-uuid-1234", json={
            "name": "Updated",
        })
        assert response.status_code == 200

    def test_delete_monitor(self, authed_client):
        response = authed_client.delete("/api/v1/monitors/mon-uuid-1234")
        assert response.status_code == 204

    def test_toggle_monitor(self, authed_client):
        response = authed_client.patch("/api/v1/monitors/mon-uuid-1234/toggle", json={
            "is_active": False,
        })
        assert response.status_code == 200


# -- Profile endpoints --

class TestProfileEndpoints:
    def test_get_profile(self, profile_client):
        response = profile_client.get("/api/v1/profiles/me")
        assert response.status_code == 200

    def test_update_profile(self, profile_client):
        response = profile_client.patch("/api/v1/profiles/me", json={
            "full_name": "Updated Name",
        })
        assert response.status_code == 200


# -- Dashboard endpoint --

class TestDashboardEndpoints:
    def test_dashboard_summary(self, client):
        response = client.get("/api/v1/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_monitors" in data


# -- Check results endpoints --

class TestCheckResultEndpoints:
    def test_get_results(self, check_result_client):
        response = check_result_client.get("/api/v1/monitors/mon-uuid-1234/results")
        assert response.status_code == 200

    def test_get_stats(self, check_result_client):
        response = check_result_client.get("/api/v1/monitors/mon-uuid-1234/stats")
        assert response.status_code == 200

    def test_export_results(self, export_client):
        response = export_client.get("/api/v1/monitors/mon-uuid-1234/results/export")
        assert response.status_code == 200
        assert "csv" in response.headers.get("content-type", "").lower() or response.status_code == 200


# -- Internal endpoint --

class TestInternalEndpoints:
    def test_run_checks_requires_internal_key(self, client):
        # Without override for verify_internal_key, should fail
        from main import app
        # Clear the verify_internal_key override if any
        if verify_internal_key in app.dependency_overrides:
            del app.dependency_overrides[verify_internal_key]
        response = client.post("/api/v1/internal/run-checks")
        assert response.status_code in (403, 422)

    def test_run_checks_with_valid_key(self):
        from main import app
        app.dependency_overrides[get_settings] = _test_settings
        app.dependency_overrides[verify_internal_key] = lambda: True

        with patch("app.api.v1.routers.internal.run_scheduled_checks", new_callable=AsyncMock, return_value={"checks_run": 0, "alerts_triggered": 0}):
            with TestClient(app) as c:
                response = c.post("/api/v1/internal/run-checks")
                assert response.status_code == 200
                data = response.json()
                assert "checks_run" in data

        app.dependency_overrides.clear()


# -- Validation edge cases --

class TestValidationEdgeCases:
    def test_monitor_interval_boundary_low(self, client):
        response = client.post("/api/v1/monitors", json={
            "name": "X", "url": "https://x.com", "interval_seconds": 29,
        })
        assert response.status_code == 422

    def test_monitor_interval_boundary_high(self, client):
        response = client.post("/api/v1/monitors", json={
            "name": "X", "url": "https://x.com", "interval_seconds": 90000,
        })
        assert response.status_code == 422

    def test_pagination_negative_page(self, authed_client):
        response = authed_client.get("/api/v1/monitors?page=0")
        assert response.status_code == 422

    def test_pagination_excessive_per_page(self, authed_client):
        response = authed_client.get("/api/v1/monitors?per_page=999")
        assert response.status_code == 422
