"""Regression guard: staged device discovery must not become a live app route.

Inspects CrownPath's actual FastAPI router without making network requests.
This does not authorize deployment or device access.
"""
from crownpath.main import app


def test_staged_device_routes_are_absent_from_real_application():
    registered_paths = {
        route.path
        for route in app.routes
        if hasattr(route, "path")
    }
    staged_paths = {
        "/internal-test/devices",
        "/test-only/devices",
        "/test-only/scoped-devices",
        "/api/devices/discover",
        "/api/devices/visible",
        "/api/device-discovery",
    }
    assert registered_paths.isdisjoint(staged_paths)


def test_no_real_app_route_uses_staged_device_access_modules():
    staged_modules = {
        "crownpath.strict_device_access",
        "crownpath.scoped_device_access",
        "crownpath.device_visibility",
    }
    for route in app.routes:
        endpoint = getattr(route, "endpoint", None)
        if endpoint is None:
            continue
        assert getattr(endpoint, "__module__", None) not in staged_modules
