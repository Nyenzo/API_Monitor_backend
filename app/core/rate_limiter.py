from slowapi import Limiter
from slowapi.util import get_remote_address

# Global rate limiter keyed by client IP address, defaulting to 60 requests per minute
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
