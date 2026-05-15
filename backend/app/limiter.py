"""
Rate limiter stub — replaced the removed slowapi-based limiter.

The original limiter (slowapi) was removed in commit 0e15461
as part of Post-Audit Opus 4.7 cleanup.

This stub provides a no-op `limit` decorator so that auth.py
(which still references @limiter.limit) can be re-enabled.
"""


class _DummyLimiter:
    """No-op rate limiter that accepts any decorator call."""

    def limit(self, _value: str):
        """Returns a no-op decorator."""

        def decorator(func):
            return func

        return decorator


limiter = _DummyLimiter()
