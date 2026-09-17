import pytest

from app.core.exceptions import BadRequestError
from app.services.openapi_service import preview_openapi_document


class TestOpenApiPreview:
    def test_extracts_static_operations_and_declared_success_status(self):
        title, operations = preview_openapi_document({
            "openapi": "3.0.3",
            "info": {"title": "Billing API"},
            "servers": [{"url": "https://api.example.com/v1"}],
            "paths": {
                "/health": {"get": {"operationId": "health", "responses": {"200": {}}}},
                "/customers/{id}": {"get": {"responses": {"200": {}}}},
            },
        })

        assert title == "Billing API"
        assert operations == [{
            "operation_id": "health",
            "name": "health",
            "url": "https://api.example.com/v1/health",
            "method": "GET",
            "expected_status": 200,
        }]

    def test_rejects_non_openapi_three_documents(self):
        with pytest.raises(BadRequestError):
            preview_openapi_document({"swagger": "2.0"})
