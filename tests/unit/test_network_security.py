import pytest

from app.core.network_security import validate_public_http_url


class TestValidatePublicHttpUrl:
    async def test_rejects_private_ip_address(self):
        with pytest.raises(ValueError, match="public IP addresses"):
            await validate_public_http_url("http://127.0.0.1/internal")

    async def test_rejects_non_http_scheme(self):
        with pytest.raises(ValueError, match="HTTP\\(S\\)"):
            await validate_public_http_url("file:///etc/passwd")
