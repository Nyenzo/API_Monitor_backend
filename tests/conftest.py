import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.core.config import Settings


# Test settings that never touch real Supabase or SMTP
@pytest.fixture
def test_settings():
    return Settings(
        supabase_url="https://test.supabase.co",
        supabase_anon_key="test-anon-key",
        supabase_service_role_key="test-service-role-key",
        internal_api_key="test-internal-key",
        cors_origins="http://localhost:3000",
        rate_limit_per_minute=100,
        smtp_host="",
        debug=True,
    )


# Fake authenticated user returned by the get_current_user dependency
@pytest.fixture
def mock_user():
    return {
        "id": "user-uuid-1234",
        "email": "test@example.com",
        "token": "fake-jwt-token",
    }


# Sample monitor dict matching the database schema
@pytest.fixture
def sample_monitor():
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": "mon-uuid-1234",
        "user_id": "user-uuid-1234",
        "name": "Test API",
        "url": "https://api.example.com/health",
        "method": "GET",
        "headers": {},
        "body": "",
        "interval_seconds": 300,
        "timeout_ms": 10000,
        "expected_status": 200,
        "expected_body_contains": "",
        "is_active": True,
        "last_checked_at": now,
        "created_at": now,
        "updated_at": now,
    }


# Sample check result dict matching the database schema
@pytest.fixture
def sample_check_result():
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": "check-uuid-1234",
        "monitor_id": "mon-uuid-1234",
        "timestamp": now,
        "status_code": 200,
        "response_time_ms": 150,
        "success": True,
        "response_size_bytes": 1024,
        "error_message": "",
        "response_snippet": '{"status": "ok"}',
        "created_at": now,
    }


# Sample alert rule dict
@pytest.fixture
def sample_alert_rule():
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": "alert-uuid-1234",
        "monitor_id": "mon-uuid-1234",
        "alert_type": "email",
        "target": "alert@example.com",
        "threshold_down_minutes": 5,
        "cooldown_minutes": 30,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }


# Mock Supabase client with chainable query builder
@pytest.fixture
def mock_supabase():
    client = MagicMock()

    # Build a chainable mock for .table().select().eq().execute() patterns
    def make_chain(data=None, count=0):
        chain = MagicMock()
        chain.data = data or []
        chain.count = count
        chain.execute.return_value = chain
        chain.select.return_value = chain
        chain.insert.return_value = chain
        chain.update.return_value = chain
        chain.delete.return_value = chain
        chain.eq.return_value = chain
        chain.in_.return_value = chain
        chain.gte.return_value = chain
        chain.or_.return_value = chain
        chain.order.return_value = chain
        chain.range.return_value = chain
        chain.limit.return_value = chain
        chain.single.return_value = chain
        return chain

    client._make_chain = make_chain
    client.table.return_value = make_chain()
    client.rpc.return_value = make_chain()
    return client


# Mock HTTP client for health check tests
@pytest.fixture
def mock_http_client():
    client = AsyncMock()
    return client
