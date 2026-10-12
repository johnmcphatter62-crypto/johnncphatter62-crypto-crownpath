import os
from unittest.mock import patch

import pytest

from crownpath.startup_guard import validate_startup


def test_production_requires_https_even_with_other_approvals():
    values = {
        "CROWNPATH_ENV": "production",
        "CROWNPATH_DATABASE_URL": "postgresql://ci-only/placeholder",
        "CROWNPATH_SECRET_KEY": "ci-only-placeholder",
        "CROWNPATH_DEMO_MODE": "false",
        "CROWNPATH_BACKUP_RESTORE_VERIFIED": "true",
        "CROWNPATH_SECURITY_TESTS_VERIFIED": "true",
        "CROWNPATH_OWNER_LAUNCH_APPROVED": "true",
    }
    with patch.dict(os.environ, values, clear=True):
        with pytest.raises(RuntimeError, match="CROWNPATH_REQUIRE_HTTPS must be true"):
            validate_startup()
        os.environ["CROWNPATH_REQUIRE_HTTPS"] = "true"
        assert validate_startup()["production_guard"] == "PASSED"


def test_staging_does_not_require_production_launch_flags():
    with patch.dict(os.environ, {"CROWNPATH_ENV": "staging"}, clear=True):
        assert validate_startup()["production_guard"] == "NOT_REQUIRED"
