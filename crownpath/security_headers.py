import os

from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # For cookie-authenticated state changes, require a matching Origin
        # or, if Origin is absent, a matching Referer. Fail closed otherwise.
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.cookies.get("crownpath_session"):
            from urllib.parse import urlsplit
            from starlette.responses import JSONResponse

            origin = request.headers.get("origin")
            source = origin if origin is not None else request.headers.get("referer")
            if source is None:
                return JSONResponse(
                    {"detail": "Request origin could not be verified."},
                    status_code=403,
                    headers={"Cache-Control": "no-store"},
                )
            if source:
                parsed = urlsplit(source)
                expected = request.url
                if (
                    parsed.scheme not in {"http", "https"}
                    or parsed.username is not None
                    or parsed.password is not None
                    or parsed.hostname != expected.hostname
                    or (parsed.port or (443 if parsed.scheme == "https" else 80))
                    != (expected.port or (443 if expected.scheme == "https" else 80))
                    or parsed.scheme != expected.scheme
                    or (origin is not None and parsed.path not in {"", "/"})
                    or (origin is not None and (parsed.query or parsed.fragment))
                ):
                    return JSONResponse(
                        {"detail": "Cross-origin state-changing request denied."},
                        status_code=403,
                        headers={"Cache-Control": "no-store"},
                    )

        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store"

        if os.getenv("CROWNPATH_REQUIRE_HTTPS", "false").lower() == "true":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
