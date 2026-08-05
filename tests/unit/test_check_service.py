import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import httpx

from app.services.check_service import execute_single_check


class TestExecuteSingleCheck:
    # Successful GET check returning expected status
    async def test_successful_check(self):
        mock_response = httpx.Response(
            status_code=200,
            content=b'{"status": "ok"}',
            request=httpx.Request("GET", "https://api.example.com/health"),
        )
        client = AsyncMock()
        client.request.return_value = mock_response

        monitor = {
            "id": "mon-1",
            "url": "https://api.example.com/health",
            "method": "GET",
            "headers": {},
            "body": "",
            "timeout_ms": 5000,
            "expected_status": 200,
            "expected_body_contains": "",
        }

        result = await execute_single_check(client, monitor)
        assert result["success"] is True
        assert result["status_code"] == 200
        assert result["response_time_ms"] >= 0
        assert result["error_message"] == ""

    # Check fails when response status doesn't match expected
    async def test_status_mismatch(self):
        mock_response = httpx.Response(
            status_code=503,
            content=b"Service Unavailable",
            request=httpx.Request("GET", "https://api.example.com"),
        )
        client = AsyncMock()
        client.request.return_value = mock_response

        monitor = {
            "id": "mon-2",
            "url": "https://api.example.com",
            "method": "GET",
            "headers": {},
            "body": "",
            "timeout_ms": 5000,
            "expected_status": 200,
            "expected_body_contains": "",
        }

        result = await execute_single_check(client, monitor)
        assert result["success"] is False
        assert result["status_code"] == 503
        assert "Expected status" in result["error_message"]

    # Check fails when body doesn't contain expected substring
    async def test_body_mismatch(self):
        mock_response = httpx.Response(
            status_code=200,
            content=b'{"status": "degraded"}',
            request=httpx.Request("GET", "https://api.example.com"),
        )
        client = AsyncMock()
        client.request.return_value = mock_response

        monitor = {
            "id": "mon-3",
            "url": "https://api.example.com",
            "method": "GET",
            "headers": {},
            "body": "",
            "timeout_ms": 5000,
            "expected_status": 200,
            "expected_body_contains": '"ok"',
        }

        result = await execute_single_check(client, monitor)
        assert result["success"] is False
        assert "missing expected content" in result["error_message"]

    # Check handles timeout gracefully
    async def test_timeout_handling(self):
        client = AsyncMock()
        client.request.side_effect = httpx.TimeoutException("timed out")

        monitor = {
            "id": "mon-4",
            "url": "https://slow.example.com",
            "method": "GET",
            "headers": {},
            "body": "",
            "timeout_ms": 1000,
            "expected_status": 200,
            "expected_body_contains": "",
        }

        result = await execute_single_check(client, monitor)
        assert result["success"] is False
        assert "timed out" in result["error_message"].lower()

    # Check handles connection errors
    async def test_connection_error(self):
        client = AsyncMock()
        client.request.side_effect = httpx.ConnectError("DNS failed")

        monitor = {
            "id": "mon-5",
            "url": "https://nonexistent.example.com",
            "method": "GET",
            "headers": {},
            "body": "",
            "timeout_ms": 5000,
            "expected_status": 200,
            "expected_body_contains": "",
        }

        result = await execute_single_check(client, monitor)
        assert result["success"] is False
        assert "Connection refused" in result["error_message"] or "DNS" in result["error_message"]

    # Check records response size accurately
    async def test_response_size_recorded(self):
        body = b"x" * 2048
        mock_response = httpx.Response(
            status_code=200,
            content=body,
            request=httpx.Request("GET", "https://api.example.com"),
        )
        client = AsyncMock()
        client.request.return_value = mock_response

        monitor = {
            "id": "mon-6",
            "url": "https://api.example.com",
            "method": "GET",
            "headers": {},
            "body": "",
            "timeout_ms": 5000,
            "expected_status": 200,
            "expected_body_contains": "",
        }

        result = await execute_single_check(client, monitor)
        assert result["response_size_bytes"] == 2048
