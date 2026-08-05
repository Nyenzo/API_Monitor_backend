import pytest
from pydantic import ValidationError
from app.schemas.auth import SignupRequest, LoginRequest, AuthResponse, RefreshRequest, UserInfo
from app.schemas.monitor import MonitorCreate, MonitorUpdate, MonitorResponse, MonitorToggle
from app.schemas.alert import AlertRuleCreate, AlertRuleUpdate
from app.schemas.profile import ProfileUpdate
from app.schemas.check_result import CheckResultResponse
from app.models.enums import HttpMethod, AlertType


# -- Auth schemas --

class TestSignupRequest:
    def test_valid_signup(self):
        req = SignupRequest(email="user@example.com", password="securepass123")
        assert req.email == "user@example.com"
        assert req.full_name == ""

    def test_signup_with_full_name(self):
        req = SignupRequest(email="user@example.com", password="securepass123", full_name="John Doe")
        assert req.full_name == "John Doe"

    def test_short_password_rejected(self):
        with pytest.raises(ValidationError):
            SignupRequest(email="user@example.com", password="short")

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            SignupRequest(email="not-an-email", password="securepass123")

    def test_empty_password_rejected(self):
        with pytest.raises(ValidationError):
            SignupRequest(email="user@example.com", password="")


class TestLoginRequest:
    def test_valid_login(self):
        req = LoginRequest(email="user@example.com", password="pass123")
        assert req.email == "user@example.com"

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="bad", password="pass123")


class TestAuthResponse:
    def test_valid_auth_response(self):
        resp = AuthResponse(
            access_token="at", refresh_token="rt",
            user_id="uid", email="a@b.com",
        )
        assert resp.access_token == "at"


# -- Monitor schemas --

class TestMonitorCreate:
    def test_valid_monitor(self):
        m = MonitorCreate(name="My API", url="https://api.example.com")
        assert m.method == HttpMethod.GET
        assert m.interval_seconds == 300
        assert m.timeout_ms == 10000

    def test_custom_method(self):
        m = MonitorCreate(name="POST API", url="https://api.example.com", method=HttpMethod.POST)
        assert m.method == HttpMethod.POST

    def test_url_without_scheme_rejected(self):
        with pytest.raises(ValidationError):
            MonitorCreate(name="Bad", url="api.example.com")

    def test_ftp_url_rejected(self):
        with pytest.raises(ValidationError):
            MonitorCreate(name="Bad", url="ftp://files.example.com")

    def test_interval_too_low(self):
        with pytest.raises(ValidationError):
            MonitorCreate(name="X", url="https://x.com", interval_seconds=10)

    def test_interval_too_high(self):
        with pytest.raises(ValidationError):
            MonitorCreate(name="X", url="https://x.com", interval_seconds=100000)

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            MonitorCreate(name="", url="https://x.com")

    def test_timeout_boundaries(self):
        with pytest.raises(ValidationError):
            MonitorCreate(name="X", url="https://x.com", timeout_ms=500)
        with pytest.raises(ValidationError):
            MonitorCreate(name="X", url="https://x.com", timeout_ms=70000)


class TestMonitorUpdate:
    def test_all_none_valid(self):
        u = MonitorUpdate()
        assert u.name is None
        assert u.url is None

    def test_partial_update(self):
        u = MonitorUpdate(name="Renamed", interval_seconds=60)
        assert u.name == "Renamed"
        assert u.interval_seconds == 60
        assert u.url is None

    def test_url_validation_on_update(self):
        with pytest.raises(ValidationError):
            MonitorUpdate(url="not-valid")

    def test_valid_url_update(self):
        u = MonitorUpdate(url="https://new.example.com")
        assert u.url == "https://new.example.com"


class TestMonitorToggle:
    def test_toggle_active(self):
        t = MonitorToggle(is_active=True)
        assert t.is_active is True

    def test_toggle_inactive(self):
        t = MonitorToggle(is_active=False)
        assert t.is_active is False


# -- Alert schemas --

class TestAlertRuleCreate:
    def test_valid_email_alert(self):
        a = AlertRuleCreate(alert_type=AlertType.EMAIL, target="alert@example.com")
        assert a.threshold_down_minutes == 5
        assert a.cooldown_minutes == 30

    def test_valid_slack_alert(self):
        a = AlertRuleCreate(alert_type=AlertType.SLACK, target="https://hooks.slack.com/xxx")
        assert a.alert_type == AlertType.SLACK

    def test_empty_target_rejected(self):
        with pytest.raises(ValidationError):
            AlertRuleCreate(alert_type=AlertType.EMAIL, target="")

    def test_low_cooldown_rejected(self):
        with pytest.raises(ValidationError):
            AlertRuleCreate(alert_type=AlertType.EMAIL, target="x@y.com", cooldown_minutes=1)


class TestAlertRuleUpdate:
    def test_all_none(self):
        u = AlertRuleUpdate()
        assert u.alert_type is None

    def test_partial(self):
        u = AlertRuleUpdate(threshold_down_minutes=10)
        assert u.threshold_down_minutes == 10


# -- Profile schemas --

class TestProfileUpdate:
    def test_all_none(self):
        p = ProfileUpdate()
        assert p.full_name is None

    def test_update_name(self):
        p = ProfileUpdate(full_name="New Name")
        assert p.full_name == "New Name"


# -- Enum coverage --

class TestEnums:
    def test_http_methods(self):
        assert HttpMethod.GET.value == "GET"
        assert HttpMethod.POST.value == "POST"
        assert len(HttpMethod) == 7

    def test_alert_types(self):
        assert AlertType.EMAIL.value == "email"
        assert AlertType.SLACK.value == "slack"
        assert AlertType.WEBHOOK.value == "webhook"
