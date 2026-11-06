import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.web import store


class PasswordPolicyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.db_patch = patch.object(store, "DB_PATH", Path(self.directory.name) / "policy.db")
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.env_patch = patch.dict(os.environ, {
            "DEMO_MODE": "false",
            "ALLOW_DEFAULT_PASSWORDS": "false",
            "ASSOCIATE_PASSWORD": "Associate@123",
            "ASSOCIATE_TWO_PASSWORD": "Associate@123",
            "ADMIN_PASSWORD": "Admin@123",
        })
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def test_defaults_remain_rejected_without_opt_in(self):
        with self.assertRaises(RuntimeError):
            store.initialize()

    def test_explicit_opt_in_allows_defaults_and_restart(self):
        with patch.dict(os.environ, {"ALLOW_DEFAULT_PASSWORDS": "true"}):
            store.initialize()
            store.initialize()
            with store.transaction() as db:
                users = store.read_all(db, "users")
                self.assertEqual(len(users), 3)
                for user in users:
                    password = "Admin@123" if user["role"] == "admin" else "Associate@123"
                    self.assertEqual(user["password"], store.password_hash(password, user["salt"]))
        with self.assertRaises(RuntimeError):
            store.initialize()
