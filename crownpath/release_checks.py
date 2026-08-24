import os
from crownpath.production_config import production_readiness

def release_checks():
    readiness = production_readiness()
    checks = dict(readiness["checks"])
    checks.update({
        "https_expected": os.getenv("CROWNPATH_REQUIRE_HTTPS", "true").lower() == "true",
        "demo_features_disabled": os.getenv("CROWNPATH_DEMO_MODE", "true").lower() == "false",
        "backup_restore_verified": os.getenv("CROWNPATH_BACKUP_RESTORE_VERIFIED", "false").lower() == "true",
        "security_tests_verified": os.getenv("CROWNPATH_SECURITY_TESTS_VERIFIED", "false").lower() == "true",
        "owner_launch_approval": os.getenv("CROWNPATH_OWNER_LAUNCH_APPROVED", "false").lower() == "true",
    })
    return {
        "checks": checks,
        "release_ready": all(checks.values())
    }
