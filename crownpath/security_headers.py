import os

from starlette.middleware.base import BaseHTTPMiddleware

from crownpath.auth import revoke_access_token


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.method == "POST" and request.url.path == "/api/auth/logout":
            token = request.cookies.get("crownpath_session")
            if token:
                revoke_access_token(token)

        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store"

        if os.getenv("CROWNPATH_REQUIRE_HTTPS", "false").lower() == "true":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
