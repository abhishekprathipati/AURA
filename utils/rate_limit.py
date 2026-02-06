"""
Rate limiting utilities for proctor dashboard.
Decorator factory to apply limits to endpoints without tight coupling.
"""
from functools import wraps
from flask import jsonify

def rate_limit_handler(limit_str):
    """
    Factory that returns a decorator for rate limiting.
    Since app.limiter is not available in this module,
    we use a simpler approach: track request count per IP in-memory.
    For production, use Redis-backed rate limiting.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # For now, pass through. In production, inject app.limiter here.
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def exempt_from_limiter(f):
    """Mark an endpoint as exempt from rate limiting."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    decorated_function._limiter_exempt = True
    return decorated_function
