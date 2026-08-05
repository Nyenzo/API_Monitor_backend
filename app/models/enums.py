from enum import Enum


# Supported HTTP methods for monitor endpoint checks
class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


# Notification channel types for alert delivery
class AlertType(str, Enum):
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"


# Lifecycle states of a single alert notification
class AlertStatus(str, Enum):
    TRIGGERED = "triggered"
    SENT = "sent"
    FAILED = "failed"
    RESOLVED = "resolved"


# Subscription tiers that control feature limits
class PlanTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"
