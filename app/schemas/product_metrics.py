from datetime import datetime

from pydantic import BaseModel


class ActivationMetricsResponse(BaseModel):
    window_start: datetime
    imported_spec_users: int
    two_contract_monitor_users: int
    first_verification_users: int
    second_verification_within_14_days_users: int
