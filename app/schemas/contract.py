from typing import Any

from pydantic import BaseModel, Field

from app.schemas.monitor import MonitorCreate, MonitorResponse


class OpenApiPreviewRequest(BaseModel):
    document: dict[str, Any]


class OpenApiOperation(BaseModel):
    operation_id: str
    name: str
    url: str
    method: str
    expected_status: int


class OpenApiPreviewResponse(BaseModel):
    title: str
    operations: list[OpenApiOperation]


class ContractMonitorBatchCreate(BaseModel):
    monitors: list[MonitorCreate] = Field(min_length=1, max_length=25)


class ContractMonitorBatchResponse(BaseModel):
    monitors: list[MonitorResponse]
