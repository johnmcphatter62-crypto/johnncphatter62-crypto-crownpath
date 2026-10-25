"""Synthetic permission-gate checks with no database connection."""
import os
import unittest
from unittest.mock import patch
from tests.payment_postgres_permission_gate import require_disposable_postgres_permission


class PaymentPermissionGateTests(unittest.TestCase):
    def setUp(self):
        self.url="postgresql+psycopg://synthetic:synthetic@localhost:5432/crownpath_test_disposable"
        self.config={
            "CROWNPATH_TEST_POSTGRES_URL":self.url,
            "CROWNPATH_DATABASE_URL":self.url,
            "CROWNPATH_ENV":"staging",
            "CROWNPATH_TEST_DB_DISPOSABLE":"YES",
            "CROWNPATH_OWNER_LAUNCH_APPROVED":"false",
        }

    def check_blocked(self, **changes):
        with patch.dict(os.environ,{**self.config,**changes},clear=True):
            with self.assertRaises(unittest.SkipTest):
                require_disposable_postgres_permission()

    def test_valid_disposable_configuration(self):
        with patch.dict(os.environ,self.config,clear=True):
            self.assertEqual(require_disposable_postgres_permission(),self.url)

    def test_production_host_blocked(self):
        self.check_blocked(CROWNPATH_TEST_POSTGRES_URL=self.url.replace("localhost","db.example.com"),CROWNPATH_DATABASE_URL=self.url.replace("localhost","db.example.com"))

    def test_non_disposable_name_blocked(self):
        self.check_blocked(CROWNPATH_TEST_POSTGRES_URL=self.url.replace("crownpath_test_disposable","crownpath_live"),CROWNPATH_DATABASE_URL=self.url.replace("crownpath_test_disposable","crownpath_live"))

    def test_mismatched_database_blocked(self):
        self.check_blocked(CROWNPATH_DATABASE_URL="postgresql://other@localhost/other")

    def test_production_environment_blocked(self):
        self.check_blocked(CROWNPATH_ENV="production")

    def test_missing_disposable_confirmation_blocked(self):
        self.check_blocked(CROWNPATH_TEST_DB_DISPOSABLE="")

    def test_owner_launch_enabled_blocked(self):
        self.check_blocked(CROWNPATH_OWNER_LAUNCH_APPROVED="true")


if __name__=="__main__":
    unittest.main()
