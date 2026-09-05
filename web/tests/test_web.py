import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app
from models import init_db, Streamer, EventSettings, WebSession, OAuthState


class TestModels(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        init_db(self.db_path)

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_streamer_get_or_create(self):
        s = Streamer(self.db_path)
        user = s.get_or_create("12345", "testuser", "TestUser")
        self.assertEqual(user["twitch_user_id"], "12345")
        self.assertEqual(user["twitch_login"], "testuser")
        self.assertEqual(user["display_name"], "TestUser")

    def test_streamer_get(self):
        s = Streamer(self.db_path)
        s.get_or_create("12345", "testuser", "TestUser")
        user = s.get("12345")
        self.assertIsNotNone(user)
        self.assertEqual(user["twitch_login"], "testuser")

    def test_streamer_get_not_found(self):
        s = Streamer(self.db_path)
        user = s.get("nonexistent")
        self.assertIsNone(user)

    def test_streamer_update_minecraft_player(self):
        s = Streamer(self.db_path)
        s.get_or_create("12345", "testuser", "TestUser")
        result = s.update_minecraft_player("12345", "MyPlayer")
        self.assertTrue(result)
        user = s.get("12345")
        self.assertEqual(user["minecraft_player"], "MyPlayer")

    def test_streamer_update_enabled(self):
        s = Streamer(self.db_path)
        s.get_or_create("12345", "testuser", "TestUser")
        s.update_enabled("12345", True)
        user = s.get("12345")
        self.assertEqual(user["enabled"], 1)

    def test_streamer_delete(self):
        s = Streamer(self.db_path)
        s.get_or_create("12345", "testuser", "TestUser")
        result = s.delete("12345")
        self.assertTrue(result)
        self.assertIsNone(s.get("12345"))

    def test_streamer_get_all(self):
        s = Streamer(self.db_path)
        s.get_or_create("111", "user1", "User1")
        s.get_or_create("222", "user2", "User2")
        all_users = s.get_all()
        self.assertEqual(len(all_users), 2)

    def test_streamer_generate_bridge_token(self):
        s = Streamer(self.db_path)
        s.get_or_create("12345", "testuser", "TestUser")
        token = s.generate_bridge_token("12345")
        self.assertTrue(len(token) > 20)
        user = s.get("12345")
        self.assertEqual(user["bridge_token"], token)

    def test_streamer_authenticate_bridge(self):
        s = Streamer(self.db_path)
        s.get_or_create("12345", "testuser", "TestUser")
        token = s.generate_bridge_token("12345")
        self.assertTrue(s.authenticate_bridge("12345", token))
        self.assertFalse(s.authenticate_bridge("12345", "wrong_token"))
        self.assertFalse(s.authenticate_bridge("99999", token))

    def test_streamer_heartbeat(self):
        s = Streamer(self.db_path)
        s.get_or_create("12345", "testuser", "TestUser")
        s.update_heartbeat("12345")
        user = s.get("12345")
        self.assertEqual(user["bridge_connected"], 1)
        self.assertIsNotNone(user["last_heartbeat"])

    def test_streamer_heartbeat_timeout(self):
        s = Streamer(self.db_path)
        s.get_or_create("12345", "testuser", "TestUser")
        from models import get_db
        conn = get_db(self.db_path)
        conn.execute("UPDATE streamers SET last_heartbeat = datetime('now', '-10 seconds'), bridge_connected = 1 WHERE twitch_user_id = '12345'")
        conn.commit()
        conn.close()
        count = s.check_heartbeat_timeout(5)
        self.assertEqual(count, 1)
        user = s.get("12345")
        self.assertEqual(user["bridge_connected"], 0)

    def test_streamer_set_bridge_connected(self):
        s = Streamer(self.db_path)
        s.get_or_create("12345", "testuser", "TestUser")
        s.set_bridge_connected("12345", True)
        user = s.get("12345")
        self.assertEqual(user["bridge_connected"], 1)
        s.set_bridge_connected("12345", False)
        user = s.get("12345")
        self.assertEqual(user["bridge_connected"], 0)

    def test_streamer_set_minecraft_connected(self):
        s = Streamer(self.db_path)
        s.get_or_create("12345", "testuser", "TestUser")
        s.set_minecraft_connected("12345", True)
        user = s.get("12345")
        self.assertEqual(user["minecraft_connected"], 1)

    def test_streamer_revoke_bridge(self):
        s = Streamer(self.db_path)
        s.get_or_create("12345", "testuser", "TestUser")
        s.generate_bridge_token("12345")
        s.set_bridge_connected("12345", True)
        s.set_minecraft_connected("12345", True)
        s.revoke_bridge("12345")
        user = s.get("12345")
        self.assertIsNone(user["bridge_token"])
        self.assertEqual(user["bridge_connected"], 0)
        self.assertEqual(user["minecraft_connected"], 0)

    def test_streamer_invalidate_twitch(self):
        s = Streamer(self.db_path)
        s.get_or_create("12345", "testuser", "TestUser", "token1", "refresh1")
        s.generate_bridge_token("12345")
        s.invalidate_twitch("12345")
        user = s.get("12345")
        self.assertIsNone(user["access_token"])
        self.assertIsNone(user["refresh_token"])
        self.assertIsNone(user["bridge_token"])

    def test_event_settings_created_with_streamer(self):
        Streamer(self.db_path).get_or_create("12345", "testuser", "TestUser")
        events = EventSettings(self.db_path).get_all("12345")
        self.assertEqual(len(events), 10)
        self.assertEqual(events[0]["event_number"], 1)
        self.assertEqual(events[0]["action"], "zombie")

    def test_event_settings_get(self):
        Streamer(self.db_path).get_or_create("12345", "testuser", "TestUser")
        event = EventSettings(self.db_path).get("12345", 1)
        self.assertIsNotNone(event)
        self.assertEqual(event["action"], "zombie")

    def test_event_settings_update(self):
        Streamer(self.db_path).get_or_create("12345", "testuser", "TestUser")
        es = EventSettings(self.db_path)
        result = es.update("12345", 1, enabled=0, cooldown=20)
        self.assertTrue(result)
        event = es.get("12345", 1)
        self.assertEqual(event["enabled"], 0)
        self.assertEqual(event["cooldown"], 20)

    def test_event_settings_update_many(self):
        Streamer(self.db_path).get_or_create("12345", "testuser", "TestUser")
        es = EventSettings(self.db_path)
        count = es.update_many("12345", [
            {"event_number": 1, "enabled": 0},
            {"event_number": 2, "cooldown": 25},
        ])
        self.assertEqual(count, 2)
        self.assertEqual(es.get("12345", 1)["enabled"], 0)
        self.assertEqual(es.get("12345", 2)["cooldown"], 25)

    def test_web_session_create_and_get(self):
        Streamer(self.db_path).get_or_create("12345", "testuser", "TestUser")
        ws = WebSession(self.db_path)
        ws.create("sess123", "12345", "2099-01-01T00:00:00")
        sess = ws.get("sess123")
        self.assertIsNotNone(sess)
        self.assertEqual(sess["twitch_user_id"], "12345")

    def test_web_session_expired(self):
        Streamer(self.db_path).get_or_create("12345", "testuser", "TestUser")
        ws = WebSession(self.db_path)
        ws.create("sess_expired", "12345", "2000-01-01T00:00:00")
        sess = ws.get("sess_expired")
        self.assertIsNone(sess)

    def test_web_session_delete(self):
        Streamer(self.db_path).get_or_create("12345", "testuser", "TestUser")
        ws = WebSession(self.db_path)
        ws.create("sess_del", "12345", "2099-01-01T00:00:00")
        result = ws.delete("sess_del")
        self.assertTrue(result)
        self.assertIsNone(ws.get("sess_del"))

    def test_web_session_delete_by_user(self):
        Streamer(self.db_path).get_or_create("12345", "testuser", "TestUser")
        ws = WebSession(self.db_path)
        ws.create("s1", "12345", "2099-01-01T00:00:00")
        ws.create("s2", "12345", "2099-01-01T00:00:00")
        count = ws.delete_by_user("12345")
        self.assertEqual(count, 2)
        self.assertIsNone(ws.get("s1"))
        self.assertIsNone(ws.get("s2"))

    def test_oauth_state_create_and_use(self):
        os_state = OAuthState(self.db_path)
        os_state.create("state_abc")
        result = os_state.use("state_abc")
        self.assertTrue(result)

    def test_oauth_state_already_used(self):
        os_state = OAuthState(self.db_path)
        os_state.create("state_used")
        os_state.use("state_used")
        result = os_state.use("state_used")
        self.assertFalse(result)

    def test_oauth_state_not_found(self):
        os_state = OAuthState(self.db_path)
        result = os_state.use("nonexistent")
        self.assertFalse(result)

    def test_isolation_between_streamers(self):
        s = Streamer(self.db_path)
        s.get_or_create("111", "user1", "User1")
        s.get_or_create("222", "user2", "User2")
        EventSettings(self.db_path).update("111", 1, enabled=0)
        self.assertEqual(EventSettings(self.db_path).get("111", 1)["enabled"], 0)
        self.assertEqual(EventSettings(self.db_path).get("222", 1)["enabled"], 1)


class TestWebApp(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.environ["DB_PATH"] = self.db_path
        os.environ["SECRET_KEY"] = "test-secret-key"
        os.environ["TWITCH_CLIENT_ID"] = "test_client_id"
        os.environ["TWITCH_CLIENT_SECRET"] = "test_client_secret"
        os.environ["TWITCH_REDIRECT_URI"] = "http://localhost:5000/auth/twitch/callback"
        os.environ["FRONTEND_URL"] = "http://localhost:4321"
        os.environ["BASE_URL"] = "http://localhost:5000"
        self.app = create_app({"TESTING": True, "DB_PATH": self.db_path})
        self.client = self.app.test_client()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)
        for key in ["DB_PATH", "SECRET_KEY", "TWITCH_CLIENT_ID", "TWITCH_CLIENT_SECRET",
                     "TWITCH_REDIRECT_URI", "FRONTEND_URL", "BASE_URL"]:
            os.environ.pop(key, None)

    def test_api_me_requires_login(self):
        resp = self.client.get("/api/me")
        self.assertEqual(resp.status_code, 401)

    def test_api_settings_requires_login(self):
        resp = self.client.get("/api/settings")
        self.assertEqual(resp.status_code, 401)

    def test_auth_twitch_redirects(self):
        resp = self.client.get("/auth/twitch")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("id.twitch.tv", resp.headers["Location"])

    def test_auth_twitch_callback_missing_params(self):
        resp = self.client.get("/auth/twitch/callback")
        self.assertEqual(resp.status_code, 400)

    def test_auth_twitch_callback_invalid_state(self):
        resp = self.client.get("/auth/twitch/callback?code=abc&state=invalid")
        self.assertEqual(resp.status_code, 403)

    def test_auth_twitch_callback_error(self):
        resp = self.client.get("/auth/twitch/callback?error=access_denied",
                               follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("error=auth_denied", resp.headers["Location"])

    def test_login_with_mocked_session(self):
        Streamer(self.db_path).get_or_create("12345", "testuser", "TestUser")
        ws = WebSession(self.db_path)
        ws.create("valid_session", "12345", "2099-01-01T00:00:00")
        with self.client.session_transaction() as sess:
            sess["session_id"] = "valid_session"
        resp = self.client.get("/api/me")
        self.assertEqual(resp.status_code, 200)

    def test_bridge_heartbeat_requires_credentials(self):
        resp = self.client.post("/api/bridge/heartbeat",
            data=json.dumps({}),
            content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_bridge_heartbeat_invalid_token(self):
        resp = self.client.post("/api/bridge/heartbeat",
            data=json.dumps({"twitch_user_id": "12345", "bridge_token": "wrong"}),
            content_type="application/json")
        self.assertEqual(resp.status_code, 403)

    def test_bridge_heartbeat_valid(self):
        s = Streamer(self.db_path)
        s.get_or_create("12345", "testuser", "TestUser")
        token = s.generate_bridge_token("12345")
        resp = self.client.post("/api/bridge/heartbeat",
            data=json.dumps({"twitch_user_id": "12345", "bridge_token": token}),
            content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["success"])

    def test_heartbeat_check(self):
        s = Streamer(self.db_path)
        s.get_or_create("12345", "testuser", "TestUser")
        s.update_heartbeat("12345")
        os.environ["HEARTBEAT_CHECK_SECRET"] = "test_secret_123"
        try:
            resp = self.client.post("/api/heartbeat-check",
                data=json.dumps({}),
                content_type="application/json",
                headers={"Authorization": "Bearer test_secret_123"})
            self.assertEqual(resp.status_code, 200)
        finally:
            del os.environ["HEARTBEAT_CHECK_SECRET"]


class TestWebAppWithUser(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        init_db(self.db_path)
        Streamer(self.db_path).get_or_create("12345", "testuser", "TestUser")
        ws = WebSession(self.db_path)
        ws.create("valid_session", "12345", "2099-01-01T00:00:00")

        os.environ["DB_PATH"] = self.db_path
        os.environ["SECRET_KEY"] = "test-secret-key"
        os.environ["TWITCH_CLIENT_ID"] = "test_client_id"
        os.environ["TWITCH_CLIENT_SECRET"] = "test_client_secret"
        os.environ["TWITCH_REDIRECT_URI"] = "http://localhost:5000/auth/twitch/callback"
        os.environ["FRONTEND_URL"] = "http://localhost:4321"
        os.environ["BASE_URL"] = "http://localhost:5000"
        self.app = create_app({"TESTING": True, "DB_PATH": self.db_path})
        self.client = self.app.test_client()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)
        for key in ["DB_PATH", "SECRET_KEY", "TWITCH_CLIENT_ID", "TWITCH_CLIENT_SECRET",
                     "TWITCH_REDIRECT_URI", "FRONTEND_URL", "BASE_URL"]:
            os.environ.pop(key, None)

    def _login(self):
        with self.client.session_transaction() as sess:
            sess["session_id"] = "valid_session"

    def _get_csrf(self):
        resp = self.client.get("/api/csrf-token")
        return json.loads(resp.data)["csrf_token"]

    def test_api_me(self):
        self._login()
        resp = self.client.get("/api/me")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["twitch_user_id"], "12345")
        self.assertEqual(data["display_name"], "TestUser")
        self.assertIn("bridge_connected", data)
        self.assertIn("minecraft_connected", data)

    def test_api_get_settings(self):
        self._login()
        resp = self.client.get("/api/settings")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(len(data["events"]), 10)

    def test_api_update_settings(self):
        self._login()
        csrf = self._get_csrf()
        resp = self.client.put("/api/settings",
            data=json.dumps({"minecraft_player": "MyMC"}),
            content_type="application/json",
            headers={"X-CSRF-Token": csrf})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["success"])

    def test_api_update_settings_no_csrf(self):
        self._login()
        resp = self.client.put("/api/settings",
            data=json.dumps({"minecraft_player": "MyMC"}),
            content_type="application/json")
        self.assertEqual(resp.status_code, 403)

    def test_api_get_events(self):
        self._login()
        resp = self.client.get("/api/events")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(len(data), 10)

    def test_api_get_single_event(self):
        self._login()
        resp = self.client.get("/api/events/1")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["action"], "zombie")

    def test_api_get_event_not_found(self):
        self._login()
        resp = self.client.get("/api/events/99")
        self.assertEqual(resp.status_code, 404)

    def test_api_update_event(self):
        self._login()
        csrf = self._get_csrf()
        resp = self.client.put("/api/events/1",
            data=json.dumps({"cooldown": 25}),
            content_type="application/json",
            headers={"X-CSRF-Token": csrf})
        self.assertEqual(resp.status_code, 200)

    def test_api_update_event_no_csrf(self):
        self._login()
        resp = self.client.put("/api/events/1",
            data=json.dumps({"cooldown": 25}),
            content_type="application/json")
        self.assertEqual(resp.status_code, 403)

    def test_api_batch_update_events(self):
        self._login()
        csrf = self._get_csrf()
        resp = self.client.put("/api/events/batch",
            data=json.dumps({"events": [
                {"event_number": 1, "enabled": False},
                {"event_number": 2, "cooldown": 30},
            ]}),
            content_type="application/json",
            headers={"X-CSRF-Token": csrf})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["updated"], 2)

    def test_logout(self):
        self._login()
        csrf = self._get_csrf()
        resp = self.client.post("/api/logout",
            data=json.dumps({}),
            content_type="application/json",
            headers={"X-CSRF-Token": csrf})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["success"])

    def test_logout_no_csrf(self):
        self._login()
        resp = self.client.post("/api/logout")
        self.assertEqual(resp.status_code, 403)

    def test_csrf_token_endpoint(self):
        self._login()
        resp = self.client.get("/api/csrf-token")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn("csrf_token", data)
        self.assertTrue(len(data["csrf_token"]) > 20)

    def test_authorization_isolation(self):
        Streamer(self.db_path).get_or_create("99999", "otheruser", "OtherUser")
        ws = WebSession(self.db_path)
        ws.create("other_session", "99999", "2099-01-01T00:00:00")

        with self.client.session_transaction() as sess:
            sess["session_id"] = "valid_session"

        resp = self.client.get("/api/me")
        data = json.loads(resp.data)
        self.assertEqual(data["twitch_user_id"], "12345")

    def test_event_update_validates_cooldown(self):
        self._login()
        csrf = self._get_csrf()
        resp = self.client.put("/api/events/1",
            data=json.dumps({"cooldown": -5}),
            content_type="application/json",
            headers={"X-CSRF-Token": csrf})
        self.assertEqual(resp.status_code, 200)
        event = EventSettings(self.db_path).get("12345", 1)
        self.assertEqual(event["cooldown"], 0)

    def test_event_update_validates_enabled_type(self):
        self._login()
        csrf = self._get_csrf()
        resp = self.client.put("/api/events/1",
            data=json.dumps({"enabled": "yes"}),
            content_type="application/json",
            headers={"X-CSRF-Token": csrf})
        self.assertEqual(resp.status_code, 200)
        event = EventSettings(self.db_path).get("12345", 1)
        self.assertEqual(event["enabled"], 0)

    def test_bridge_register(self):
        self._login()
        csrf = self._get_csrf()
        resp = self.client.post("/api/bridge/register",
            data=json.dumps({}),
            content_type="application/json",
            headers={"X-CSRF-Token": csrf})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn("bridge_token", data)
        self.assertEqual(data["twitch_user_id"], "12345")

    def test_bridge_disconnect(self):
        self._login()
        csrf = self._get_csrf()
        Streamer(self.db_path).set_bridge_connected("12345", True)
        resp = self.client.post("/api/bridge/disconnect",
            data=json.dumps({}),
            content_type="application/json",
            headers={"X-CSRF-Token": csrf})
        self.assertEqual(resp.status_code, 200)
        user = Streamer(self.db_path).get("12345")
        self.assertEqual(user["bridge_connected"], 0)

    def test_session_invalidated_on_logout(self):
        self._login()
        csrf = self._get_csrf()
        self.client.post("/api/logout",
            data=json.dumps({}),
            content_type="application/json",
            headers={"X-CSRF-Token": csrf})
        resp = self.client.get("/api/me")
        self.assertEqual(resp.status_code, 401)


class TestTwitchOAuth(unittest.TestCase):
    def test_authorization_url(self):
        from twitch_oauth import TwitchOAuth
        oauth = TwitchOAuth("client123", "secret456", "http://localhost:5000/auth/twitch/callback")
        url = oauth.get_authorization_url("test_state")
        self.assertIn("client_id=client123", url)
        self.assertIn("state=test_state", url)
        self.assertIn("response_type=code", url)
        self.assertIn("redirect_uri=", url)

    def test_generate_state(self):
        from twitch_oauth import generate_state
        state1 = generate_state()
        state2 = generate_state()
        self.assertNotEqual(state1, state2)
        self.assertTrue(len(state1) > 20)


if __name__ == "__main__":
    unittest.main()
