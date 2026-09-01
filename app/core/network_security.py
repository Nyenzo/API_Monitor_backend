import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit


async def validate_public_http_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only absolute HTTP(S) URLs are supported")

    try:
        addresses = await asyncio.get_running_loop().getaddrinfo(
            parsed.hostname,
            None,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise ValueError("Target hostname could not be resolved") from exc

    resolved_ips = {address[4][0] for address in addresses}
    if not resolved_ips or any(not ipaddress.ip_address(ip).is_global for ip in resolved_ips):
        raise ValueError("Target must resolve exclusively to public IP addresses")
