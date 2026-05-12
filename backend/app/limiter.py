"""
Rate limiter — wrapper unifié.
Utilise le middleware custom (rate_limit_middleware.py) pour la vraie limitation.
Les décorateurs @limiter.limit() sont conservés pour la documentation mais sont no-op :
la limitation réelle est gérée par le middleware HTTP.
"""
import os

TESTING = os.getenv("TESTING", "").lower() == "true"


class _Limiter:
    """Limiter unifié — délègue au middleware HTTP."""

    def limit(self, *args, **kwargs):
        """Décorateur no-op : la limitation est gérée par le middleware."""

        def decorator(f):
            return f

        return decorator


# Instance partagée — utilisée comme décorateur dans routes.py et auth.py
limiter = _Limiter()
