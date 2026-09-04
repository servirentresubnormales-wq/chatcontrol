import unittest
import tempfile
import os
import json
from datetime import datetime, timedelta

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models import init_db, Streamer, WebSession, EmailVerification, LinkCode, StreamerLink
from app import create_app


class TestEmailVerification(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        init_db(self.db_path)
        os.environ["DB_PATH"] = self.db_path
        os.environ["SECRET_KEY"] = "test-secret-key"
        os.environ["TWITCH_CLIENT_ID"] = "test_client_id"
        os.environ["TWITCH_CLIENT_SECRET"] = "test_client_secret"
        os.environ["TWITCH_REDIRECT_URI"] = "http://localhost:5000/auth/twitch/callback"
        os.environ["FRONTEND_URL"] = "http://localhost:4321"
        self.app = create_app({"TESTING": True, "DB_PATH": self.db_path})
        self.client = self.app.test_client()
        Streamer(self.db_path).get_or_create("12345", "testuser", "TestUser", email="test@example.com")
        ws = WebSession(self.db_path)
        ws.create("valid_session", "12345", "2099-01-01T00:00:00")
        os.environ["EMAIL_VERIFICATION_TTL"] = "900"

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)
        for k in ["DB_PATH", "SECRET_KEY", "TWITCH_CLIENT_ID", "TWITCH_CLIENT_SECRET", "TWITCH_REDIRECT_URI", "FRONTEND_URL", "EMAIL_VERIFICATION_TTL"]:
            os.environ.pop(k, None)

    def _login(self):
        with self.client.session_transaction() as sess:
            sess["session_id"] = "valid_session"

    def _get_csrf(self):
        resp = self.client.get("/api/csrf-token")
        return json.loads(resp.data)["csrf_token"]

    def test_send_requires_session(self):
        resp = self.client.post("/api/email/send", json={})
        self.assertEqual(resp.status_code, 401)

    def test_send_creates_token(self):
        self._login()
        resp = self.client.post("/api/email/send", json={},
            headers={"X-CSRF-Token": self._get_csrf()})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn("expires_at", data)

    def test_send_already_verified(self):
        self._login()
        conn = self.app.config.get("DB_PATH") or self.db_path
        import sqlite3
        db = sqlite3.connect(self.db_path)
        db.execute("UPDATE streamers SET email_verified = 1 WHERE twitch_user_id = '12345'")
        db.commit()
        db.close()
        resp = self.client.post("/api/email/send", json={},
            headers={"X-CSRF-Token": self._get_csrf()})
        self.assertEqual(resp.status_code, 400)

    def test_status_when_not_verified(self):
        self._login()
        resp = self.client.get("/api/email/status")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertFalse(data["verified"])

    def test_confirm_valid_token(self):
        self._login()
        ev = EmailVerification(self.db_path)
        token, _ = ev.create("12345", "test@example.com")
        resp = self.client.post("/api/email/confirm", json={"token": token},
            headers={"X-CSRF-Token": self._get_csrf()})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["verified"])

    def test_confirm_invalid_token(self):
        self._login()
        resp = self.client.post("/api/email/confirm", json={"token": "invalid_token"},
            headers={"X-CSRF-Token": self._get_csrf()})
        self.assertEqual(resp.status_code, 400)

    def test_confirm_expired_token(self):
        self._login()
        ev = EmailVerification(self.db_path)
        import sqlite3
        db = sqlite3.connect(self.db_path)
        token = "testtoken123"
        import hashlib
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        past = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        db.execute("INSERT INTO email_verifications (twitch_user_id, email, token_hash, expires_at) VALUES (?, ?, ?, ?)",
            ("12345", "test@example.com", token_hash, past))
        db.commit()
        db.close()
        resp = self.client.post("/api/email/confirm", json={"token": token},
            headers={"X-CSRF-Token": self._get_csrf()})
        self.assertEqual(resp.status_code, 400)

    def test_confirm_used_token(self):
        self._login()
        ev = EmailVerification(self.db_path)
        token, _ = ev.create("12345", "test@example.com")
        self.client.post("/api/email/confirm", json={"token": token},
            headers={"X-CSRF-Token": self._get_csrf()})
        resp = self.client.post("/api/email/confirm", json={"token": token},
            headers={"X-CSRF-Token": self._get_csrf()})
        self.assertEqual(resp.status_code, 400)


class TestLinking(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        init_db(self.db_path)
        os.environ["DB_PATH"] = self.db_path
        os.environ["SECRET_KEY"] = "test-secret-key"
        os.environ["TWITCH_CLIENT_ID"] = "test_client_id"
        os.environ["TWITCH_CLIENT_SECRET"] = "test_client_secret"
        os.environ["TWITCH_REDIRECT_URI"] = "http://localhost:5000/auth/twitch/callback"
        os.environ["FRONTEND_URL"] = "http://localhost:4321"
        os.environ["LINK_CODE_TTL"] = "60"
        self.app = create_app({"TESTING": True, "DB_PATH": self.db_path})
        self.client = self.app.test_client()
        Streamer(self.db_path).get_or_create("12345", "testuser", "TestUser", email="test@example.com")
        ws = WebSession(self.db_path)
        ws.create("valid_session", "12345", "2099-01-01T00:00:00")
        import sqlite3
        db = sqlite3.connect(self.db_path)
        db.execute("UPDATE streamers SET email_verified = 1 WHERE twitch_user_id = '12345'")
        db.commit()
        db.close()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)
        for k in ["DB_PATH", "SECRET_KEY", "TWITCH_CLIENT_ID", "TWITCH_CLIENT_SECRET", "TWITCH_REDIRECT_URI", "FRONTEND_URL", "LINK_CODE_TTL"]:
            os.environ.pop(k, None)

    def _login(self):
        with self.client.session_transaction() as sess:
            sess["session_id"] = "valid_session"

    def _get_csrf(self):
        resp = self.client.get("/api/csrf-token")
        return json.loads(resp.data)["csrf_token"]

    def _register_bridge(self):
        resp = self.client.post("/api/bridge/register", json={},
            headers={"X-CSRF-Token": self._get_csrf()})
        return json.loads(resp.data)["bridge_token"]

    def test_start_requires_session(self):
        resp = self.client.post("/api/link/start", json={})
        self.assertEqual(resp.status_code, 401)

    def test_start_requires_verified_email(self):
        import sqlite3
        db = sqlite3.connect(self.db_path)
        db.execute("UPDATE streamers SET email_verified = 0 WHERE twitch_user_id = '12345'")
        db.commit()
        db.close()
        self._login()
        resp = self.client.post("/api/link/start", json={},
            headers={"X-CSRF-Token": self._get_csrf()})
        self.assertEqual(resp.status_code, 403)

    def test_start_creates_code(self):
        self._login()
        resp = self.client.post("/api/link/start", json={},
            headers={"X-CSRF-Token": self._get_csrf()})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn("link_code", data)
        self.assertIn("expires_at", data)
        self.assertRegex(data["link_code"], r"^\d{6}$")

    def test_start_already_linked(self):
        self._login()
        import sqlite3
        db = sqlite3.connect(self.db_path)
        db.execute("INSERT INTO streamer_links (twitch_user_id, bridge_instance_id, status) VALUES (?, ?, 'LINKED')", ("12345", "bridge-1"))
        db.commit()
        db.close()
        resp = self.client.post("/api/link/start", json={},
            headers={"X-CSRF-Token": self._get_csrf()})
        self.assertEqual(resp.status_code, 409)

    def test_status_when_unlinked(self):
        self._login()
        resp = self.client.get("/api/link/status")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertFalse(data["linked"])

    def test_status_when_linked(self):
        self._login()
        import sqlite3
        db = sqlite3.connect(self.db_path)
        db.execute("INSERT INTO streamer_links (twitch_user_id, bridge_instance_id, status) VALUES (?, ?, 'LINKED')", ("12345", "bridge-1"))
        db.commit()
        db.close()
        resp = self.client.get("/api/link/status")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["linked"])

    def test_complete_requires_bridge_auth(self):
        resp = self.client.post("/api/link/complete", json={
            "twitch_user_id": "12345", "bridge_token": "wrong", "link_code": "123456"
        })
        self.assertEqual(resp.status_code, 403)

    def test_complete_valid_code(self):
        self._login()
        bridge_token = self._register_bridge()
        lc = LinkCode(self.db_path)
        code, _ = lc.create("12345")
        resp = self.client.post("/api/link/complete", json={
            "twitch_user_id": "12345", "bridge_token": bridge_token,
            "link_code": code, "bridge_instance_id": "test-bridge"
        })
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["success"])

    def test_complete_invalid_code(self):
        self._login()
        bridge_token = self._register_bridge()
        resp = self.client.post("/api/link/complete", json={
            "twitch_user_id": "12345", "bridge_token": bridge_token,
            "link_code": "000000", "bridge_instance_id": "test-bridge"
        })
        self.assertEqual(resp.status_code, 400)

    def test_complete_expired_code(self):
        self._login()
        bridge_token = self._register_bridge()
        import sqlite3, hashlib, secrets
        db = sqlite3.connect(self.db_path)
        code = "123456"
        salt = secrets.token_hex(16)
        code_hash = hashlib.sha256((salt + code).encode()).hexdigest()
        past = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        db.execute("INSERT INTO link_codes (twitch_user_id, code_hash, code_salt, expires_at) VALUES (?, ?, ?, ?)",
            ("12345", code_hash, salt, past))
        db.commit()
        db.close()
        resp = self.client.post("/api/link/complete", json={
            "twitch_user_id": "12345", "bridge_token": bridge_token,
            "link_code": code, "bridge_instance_id": "test-bridge"
        })
        self.assertEqual(resp.status_code, 400)

    def test_revoke_requires_session(self):
        resp = self.client.post("/api/link/revoke", json={})
        self.assertEqual(resp.status_code, 401)

    def test_revoke_own_link(self):
        self._login()
        import sqlite3
        db = sqlite3.connect(self.db_path)
        db.execute("INSERT INTO streamer_links (twitch_user_id, bridge_instance_id, status) VALUES (?, ?, 'LINKED')", ("12345", "bridge-1"))
        db.commit()
        db.close()
        resp = self.client.post("/api/link/revoke", json={},
            headers={"X-CSRF-Token": self._get_csrf()})
        self.assertEqual(resp.status_code, 200)
        link = StreamerLink(self.db_path).get("12345")
        self.assertIsNone(link)

    def test_revoke_no_link(self):
        self._login()
        resp = self.client.post("/api/link/revoke", json={},
            headers={"X-CSRF-Token": self._get_csrf()})
        self.assertEqual(resp.status_code, 404)

    def test_code_is_hashed(self):
        self._login()
        resp = self.client.post("/api/link/start", json={},
            headers={"X-CSRF-Token": self._get_csrf()})
        data = json.loads(resp.data)
        import sqlite3
        db = sqlite3.connect(self.db_path)
        row = db.execute("SELECT code_hash FROM link_codes WHERE twitch_user_id = '12345'").fetchone()
        db.close()
        self.assertIsNotNone(row)
        self.assertNotEqual(row[0], data["link_code"])
        self.assertEqual(len(row[0]), 64)


if __name__ == "__main__":
    unittest.main()
