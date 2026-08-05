import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone

from app.services.monitor_service import (
    list_monitors, get_monitor, create_monitor, update_monitor,
    delete_monitor, toggle_monitor,
)
from app.services.export_service import export_results_csv
from app.schemas.monitor import MonitorCreate, MonitorUpdate
from app.core.exceptions import NotFoundError
from app.models.enums import HttpMethod


class TestMonitorService:
    # Helper to build a chainable supabase mock that returns specified data
    def _make_supabase(self, data=None, count=0):
        chain = MagicMock()
        result = MagicMock()
        result.data = data if data is not None else []
        result.count = count
        chain.execute.return_value = result
        for method in ["select", "insert", "update", "delete", "eq", "or_", "order", "range", "single", "in_", "gte", "limit"]:
            getattr(chain, method).return_value = chain
        sb = MagicMock()
        sb.table.return_value = chain
        return sb, chain

    async def test_list_monitors_returns_data(self, sample_monitor):
        sb, chain = self._make_supabase(data=[sample_monitor], count=1)
        monitors, total = await list_monitors(sb, "user-uuid-1234")
        assert total == 1
        assert monitors[0]["name"] == "Test API"

    async def test_list_monitors_empty(self):
        sb, chain = self._make_supabase(data=[], count=0)
        monitors, total = await list_monitors(sb, "user-uuid-1234")
        assert total == 0
        assert monitors == []

    async def test_list_monitors_with_search(self, sample_monitor):
        sb, chain = self._make_supabase(data=[sample_monitor], count=1)
        monitors, total = await list_monitors(sb, "user-uuid-1234", search="Test")
        chain.or_.assert_called_once()
        assert total == 1

    async def test_list_monitors_with_active_filter(self, sample_monitor):
        sb, chain = self._make_supabase(data=[sample_monitor], count=1)
        await list_monitors(sb, "user-uuid-1234", is_active=True)
        # eq called for user_id + is_active
        assert chain.eq.call_count >= 2

    async def test_get_monitor_found(self, sample_monitor):
        sb, chain = self._make_supabase(data=sample_monitor)
        result = await get_monitor(sb, "mon-uuid-1234", "user-uuid-1234")
        assert result["name"] == "Test API"

    async def test_get_monitor_not_found(self):
        sb, chain = self._make_supabase(data=None)
        with pytest.raises(NotFoundError):
            await get_monitor(sb, "nonexistent", "user-uuid-1234")

    async def test_create_monitor(self, sample_monitor):
        sb, chain = self._make_supabase(data=[sample_monitor])
        payload = MonitorCreate(name="Test API", url="https://api.example.com/health")
        result = await create_monitor(sb, "user-uuid-1234", payload)
        assert result["name"] == "Test API"
        chain.insert.assert_called_once()

    async def test_update_monitor(self, sample_monitor):
        # get_monitor needs to succeed, then update returns data
        sb, chain = self._make_supabase(data=[{**sample_monitor, "name": "Updated"}])
        # Mock get_monitor to not raise
        chain.single.return_value = chain
        result_mock = MagicMock()
        result_mock.data = sample_monitor
        chain.execute.side_effect = [result_mock, MagicMock(data=[{**sample_monitor, "name": "Updated"}])]

        payload = MonitorUpdate(name="Updated")
        result = await update_monitor(sb, "mon-uuid-1234", "user-uuid-1234", payload)
        assert result["name"] == "Updated"

    async def test_delete_monitor(self, sample_monitor):
        sb, chain = self._make_supabase(data=sample_monitor)
        await delete_monitor(sb, "mon-uuid-1234", "user-uuid-1234")
        chain.delete.assert_called()

    async def test_toggle_monitor(self, sample_monitor):
        toggled = {**sample_monitor, "is_active": False}
        sb, chain = self._make_supabase(data=[toggled])
        result_mock = MagicMock()
        result_mock.data = sample_monitor
        chain.execute.side_effect = [result_mock, MagicMock(data=[toggled])]

        result = await toggle_monitor(sb, "mon-uuid-1234", "user-uuid-1234", False)
        assert result["is_active"] is False


class TestExportService:
    async def test_export_csv_generates_header(self):
        chain = MagicMock()
        result = MagicMock()
        result.data = [
            {
                "timestamp": "2025-01-01T00:00:00Z",
                "status_code": 200,
                "response_time_ms": 100,
                "success": True,
                "response_size_bytes": 512,
                "error_message": "",
            }
        ]
        chain.execute.return_value = result
        for m in ["select", "eq", "gte", "order"]:
            getattr(chain, m).return_value = chain
        sb = MagicMock()
        sb.table.return_value = chain

        csv_output = await export_results_csv(sb, "mon-uuid-1234", "user-uuid-1234", 24)
        assert "timestamp" in csv_output
        assert "status_code" in csv_output
        assert "200" in csv_output

    async def test_export_csv_empty(self):
        chain = MagicMock()
        result = MagicMock()
        result.data = []
        chain.execute.return_value = result
        for m in ["select", "eq", "gte", "order"]:
            getattr(chain, m).return_value = chain
        sb = MagicMock()
        sb.table.return_value = chain

        csv_output = await export_results_csv(sb, "mon-uuid-1234", "user-uuid-1234", 24)
        lines = csv_output.strip().split("\n")
        assert len(lines) == 1  # Header only
