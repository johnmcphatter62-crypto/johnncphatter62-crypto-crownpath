"""Synthetic origin-verification checks for cookie-authenticated mutations."""
import asyncio

from starlette.requests import Request
from starlette.responses import Response

from crownpath.security_headers import SecurityHeadersMiddleware


def _check(origin=None, referer=None):
    headers = [(b"host", b"crownpath.test"), (b"cookie", b"crownpath_session=synthetic")]
    if origin is not None:
        headers.append((b"origin", origin.encode()))
    if referer is not None:
        headers.append((b"referer", referer.encode()))
    scope = {
        "type": "http", "method": "POST", "scheme": "https",
        "server": ("crownpath.test", 443), "path": "/api/owner/curriculum/lesson-versions",
        "root_path": "", "query_string": b"", "headers": headers,
    }
    request = Request(scope)
    reached = []

    async def next_handler(_request):
        reached.append(True)
        return Response(status_code=204)

    middleware = SecurityHeadersMiddleware(app=lambda *args: None)
    response = asyncio.run(middleware.dispatch(request, next_handler))
    return response.status_code, bool(reached)


def test_same_origin_cookie_mutation_allowed():
    assert _check(origin="https://crownpath.test") == (204, True)
    assert _check(referer="https://crownpath.test/editor") == (204, True)


def test_cross_origin_and_missing_origin_denied():
    for origin, referer in [
        (None, None),
        ("https://attacker.test", None),
        ("http://crownpath.test", None),
        ("https://crownpath.test:444", None),
        ("https://crownpath.test", "https://attacker.test/editor"),
    ]:
        # When Origin is present, it takes precedence over Referer.
        if origin == "https://crownpath.test":
            assert _check(origin=origin, referer=referer) == (204, True)
        else:
            assert _check(origin=origin, referer=referer) == (403, False)
