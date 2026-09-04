import sqlite3
import os
import json
import secrets
import hashlib
import hmac as hmac_mod
from typing import Optional
from datetime import datetime, timedelta

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "chatcontrol.db")


def _get_db_path() -> str:
    return os.environ.get("DB_PATH") or DEFAULT_DB_PATH

DEFAULT_EVENT_CONFIG = {
    1: {"action": "zombie", "enabled": True, "cooldown": 10, "params": {"count": 3, "radius": 5}},
    2: {"action": "spiders", "enabled": True, "cooldown": 10, "params": {"count": 2, "radius": 5}},
    3: {"action": "slowness", "enabled": True, "cooldown": 15, "params": {"duration": 10, "amplifier": 1}},
    4: {"action": "blindness", "enabled": True, "cooldown": 15, "params": {"duration": 8, "amplifier": 1}},
    5: {"action": "creeper", "enabled": True, "cooldown": 30, "params": {"count": 1, "radius": 3}},
    6: {"action": "storm", "enabled": True, "cooldown": 60, "params": {"duration": 60, "thunder": True}},
    7: {"action": "random_teleport", "enabled": True, "cooldown": 20, "params": {"radius": 100}},
    8: {"action": "explosion", "enabled": True, "cooldown": 30, "params": {"power": 4, "radius": 10}},
    9: {"action": "random_event", "enabled": True, "cooldown": 45, "params": {}},
    10: {"action": "chickens", "enabled": True, "cooldown": 0, "params": {"count": 10, "radius": 5}},
}


def get_db(db_path: str = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: str = None) -> None:
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    conn = get_db(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS streamers (
            twitch_user_id TEXT PRIMARY KEY,
            twitch_login TEXT NOT NULL,
            display_name TEXT NOT NULL,
            access_token TEXT,
            refresh_token TEXT,
            minecraft_player TEXT DEFAULT '',
            enabled INTEGER DEFAULT 0,
            bridge_connected INTEGER DEFAULT 0,
            minecraft_connected INTEGER DEFAULT 0,
            last_heartbeat TIMESTAMP,
            bridge_token TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS event_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            twitch_user_id TEXT NOT NULL,
            event_number INTEGER NOT NULL,
            action TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            cooldown INTEGER DEFAULT 10,
            params TEXT DEFAULT '{}',
            display_name TEXT,
            FOREIGN KEY (twitch_user_id) REFERENCES streamers(twitch_user_id) ON DELETE CASCADE,
            UNIQUE(twitch_user_id, event_number)
        );

        CREATE TABLE IF NOT EXISTS web_sessions (
            session_id TEXT PRIMARY KEY,
            twitch_user_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (twitch_user_id) REFERENCES streamers(twitch_user_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS oauth_states (
            state TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            used INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS email_verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            twitch_user_id TEXT NOT NULL,
            email TEXT NOT NULL,
            token_hash TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (twitch_user_id) REFERENCES streamers(twitch_user_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_email_verifications_token
            ON email_verifications(token_hash);
        CREATE INDEX IF NOT EXISTS idx_email_verifications_user
            ON email_verifications(twitch_user_id);

        CREATE TABLE IF NOT EXISTS link_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            twitch_user_id TEXT NOT NULL,
            code_hash TEXT NOT NULL,
            code_salt TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (twitch_user_id) REFERENCES streamers(twitch_user_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_link_codes_hash
            ON link_codes(code_hash);
        CREATE INDEX IF NOT EXISTS idx_link_codes_user_active
            ON link_codes(twitch_user_id, used, expires_at);

        CREATE TABLE IF NOT EXISTS streamer_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            twitch_user_id TEXT NOT NULL UNIQUE,
            bridge_instance_id TEXT NOT NULL DEFAULT '',
            link_code_id INTEGER,
            status TEXT DEFAULT 'LINKED' CHECK(status IN ('LINKED', 'REVOKED')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (twitch_user_id) REFERENCES streamers(twitch_user_id) ON DELETE CASCADE,
            FOREIGN KEY (link_code_id) REFERENCES link_codes(id) ON DELETE SET NULL
        );
    """)
    conn.commit()

    try:
        conn.execute("ALTER TABLE streamers ADD COLUMN email TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE streamers ADD COLUMN email_verified INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


class Streamer:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or _get_db_path()

    def get_or_create(self, twitch_user_id: str, twitch_login: str, display_name: str,
                      access_token: str = None, refresh_token: str = None, email: str = None) -> dict:
        conn = get_db(self.db_path)
        try:
            existing = conn.execute(
                "SELECT * FROM streamers WHERE twitch_user_id = ?", (twitch_user_id,)
            ).fetchone()

            if existing:
                conn.execute("""
                    UPDATE streamers SET twitch_login = ?, display_name = ?,
                    access_token = COALESCE(?, access_token),
                    refresh_token = COALESCE(?, refresh_token),
                    email = COALESCE(?, email),
                    updated_at = CURRENT_TIMESTAMP
                    WHERE twitch_user_id = ?
                """, (twitch_login, display_name, access_token, refresh_token, email, twitch_user_id))
                conn.commit()
                return conn.execute(
                    "SELECT * FROM streamers WHERE twitch_user_id = ?", (twitch_user_id,)
                ).fetchone()
            else:
                conn.execute("""
                    INSERT INTO streamers (twitch_user_id, twitch_login, display_name, access_token, refresh_token, email)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (twitch_user_id, twitch_login, display_name, access_token, refresh_token, email))
                conn.commit()

                for num, cfg in DEFAULT_EVENT_CONFIG.items():
                    conn.execute("""
                        INSERT INTO event_settings (twitch_user_id, event_number, action, enabled, cooldown, params)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (twitch_user_id, num, cfg["action"], cfg["enabled"], cfg["cooldown"],
                          json.dumps(cfg["params"])))
                conn.commit()

                return conn.execute(
                    "SELECT * FROM streamers WHERE twitch_user_id = ?", (twitch_user_id,)
                ).fetchone()
        finally:
            conn.close()

    def get(self, twitch_user_id: str) -> Optional[dict]:
        conn = get_db(self.db_path)
        try:
            row = conn.execute(
                "SELECT * FROM streamers WHERE twitch_user_id = ?", (twitch_user_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_minecraft_player(self, twitch_user_id: str, minecraft_player: str) -> bool:
        conn = get_db(self.db_path)
        try:
            cursor = conn.execute("""
                UPDATE streamers SET minecraft_player = ?, updated_at = CURRENT_TIMESTAMP
                WHERE twitch_user_id = ?
            """, (minecraft_player, twitch_user_id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def update_enabled(self, twitch_user_id: str, enabled: bool) -> bool:
        conn = get_db(self.db_path)
        try:
            cursor = conn.execute("""
                UPDATE streamers SET enabled = ?, updated_at = CURRENT_TIMESTAMP
                WHERE twitch_user_id = ?
            """, (1 if enabled else 0, twitch_user_id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete(self, twitch_user_id: str) -> bool:
        conn = get_db(self.db_path)
        try:
            cursor = conn.execute("DELETE FROM streamers WHERE twitch_user_id = ?", (twitch_user_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_all(self) -> list:
        conn = get_db(self.db_path)
        try:
            rows = conn.execute("SELECT * FROM streamers").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def generate_bridge_token(self, twitch_user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        conn = get_db(self.db_path)
        try:
            conn.execute("""
                UPDATE streamers SET bridge_token = ?, updated_at = CURRENT_TIMESTAMP
                WHERE twitch_user_id = ?
            """, (token, twitch_user_id))
            conn.commit()
            return token
        finally:
            conn.close()

    def authenticate_bridge(self, twitch_user_id: str, bridge_token: str) -> bool:
        conn = get_db(self.db_path)
        try:
            row = conn.execute(
                "SELECT * FROM streamers WHERE twitch_user_id = ? AND bridge_token = ?",
                (twitch_user_id, bridge_token)
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    def update_heartbeat(self, twitch_user_id: str) -> bool:
        conn = get_db(self.db_path)
        try:
            cursor = conn.execute("""
                UPDATE streamers SET last_heartbeat = CURRENT_TIMESTAMP,
                bridge_connected = 1, updated_at = CURRENT_TIMESTAMP
                WHERE twitch_user_id = ?
            """, (twitch_user_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def set_bridge_connected(self, twitch_user_id: str, connected: bool) -> bool:
        conn = get_db(self.db_path)
        try:
            cursor = conn.execute("""
                UPDATE streamers SET bridge_connected = ?,
                updated_at = CURRENT_TIMESTAMP
                WHERE twitch_user_id = ?
            """, (1 if connected else 0, twitch_user_id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def set_minecraft_connected(self, twitch_user_id: str, connected: bool) -> bool:
        conn = get_db(self.db_path)
        try:
            cursor = conn.execute("""
                UPDATE streamers SET minecraft_connected = ?,
                updated_at = CURRENT_TIMESTAMP
                WHERE twitch_user_id = ?
            """, (1 if connected else 0, twitch_user_id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def check_heartbeat_timeout(self, timeout_seconds: int = 60) -> int:
        conn = get_db(self.db_path)
        try:
            cursor = conn.execute("""
                UPDATE streamers SET bridge_connected = 0
                WHERE bridge_connected = 1
                AND last_heartbeat IS NOT NULL
                AND last_heartbeat < datetime('now', ?)
            """, (f"-{timeout_seconds} seconds",))
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def revoke_bridge(self, twitch_user_id: str) -> bool:
        conn = get_db(self.db_path)
        try:
            cursor = conn.execute("""
                UPDATE streamers SET bridge_token = NULL, bridge_connected = 0,
                minecraft_connected = 0, updated_at = CURRENT_TIMESTAMP
                WHERE twitch_user_id = ?
            """, (twitch_user_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def invalidate_twitch(self, twitch_user_id: str) -> bool:
        conn = get_db(self.db_path)
        try:
            cursor = conn.execute("""
                UPDATE streamers SET access_token = NULL, refresh_token = NULL,
                bridge_token = NULL, bridge_connected = 0, minecraft_connected = 0,
                updated_at = CURRENT_TIMESTAMP
                WHERE twitch_user_id = ?
            """, (twitch_user_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()


class EventSettings:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or _get_db_path()

    def get_all(self, twitch_user_id: str) -> list:
        conn = get_db(self.db_path)
        try:
            rows = conn.execute(
                "SELECT * FROM event_settings WHERE twitch_user_id = ? ORDER BY event_number",
                (twitch_user_id,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get(self, twitch_user_id: str, event_number: int) -> Optional[dict]:
        conn = get_db(self.db_path)
        try:
            row = conn.execute(
                "SELECT * FROM event_settings WHERE twitch_user_id = ? AND event_number = ?",
                (twitch_user_id, event_number)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update(self, twitch_user_id: str, event_number: int, **kwargs) -> bool:
        conn = get_db(self.db_path)
        try:
            allowed = {"enabled", "cooldown", "params", "display_name"}
            updates = {k: v for k, v in kwargs.items() if k in allowed}
            if not updates:
                return False

            if "enabled" in updates:
                updates["enabled"] = 1 if updates["enabled"] is True else 0
            if "cooldown" in updates:
                updates["cooldown"] = max(0, int(updates["cooldown"]))
            if "params" in updates and isinstance(updates["params"], dict):
                updates["params"] = json.dumps(updates["params"])

            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [twitch_user_id, event_number]

            cursor = conn.execute(
                f"UPDATE event_settings SET {set_clause} WHERE twitch_user_id = ? AND event_number = ?",
                values
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def update_many(self, twitch_user_id: str, events: list) -> int:
        conn = get_db(self.db_path)
        try:
            count = 0
            for event in events:
                num = event.get("event_number")
                if num is None:
                    continue
                updates = {}
                if "enabled" in event:
                    updates["enabled"] = 1 if event["enabled"] is True else 0
                if "cooldown" in event:
                    updates["cooldown"] = event["cooldown"]
                if "params" in event:
                    updates["params"] = json.dumps(event["params"])
                if "display_name" in event:
                    updates["display_name"] = event["display_name"]

                if updates:
                    set_clause = ", ".join(f"{k} = ?" for k in updates)
                    values = list(updates.values()) + [twitch_user_id, num]
                    cursor = conn.execute(
                        f"UPDATE event_settings SET {set_clause} WHERE twitch_user_id = ? AND event_number = ?",
                        values
                    )
                    count += cursor.rowcount
            conn.commit()
            return count
        finally:
            conn.close()


class WebSession:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or _get_db_path()

    def create(self, session_id: str, twitch_user_id: str, expires_at: str) -> None:
        conn = get_db(self.db_path)
        try:
            conn.execute(
                "INSERT INTO web_sessions (session_id, twitch_user_id, expires_at) VALUES (?, ?, ?)",
                (session_id, twitch_user_id, expires_at)
            )
            conn.commit()
        finally:
            conn.close()

    def get(self, session_id: str) -> Optional[dict]:
        conn = get_db(self.db_path)
        try:
            row = conn.execute(
                "SELECT * FROM web_sessions WHERE session_id = ? AND expires_at > CURRENT_TIMESTAMP",
                (session_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def delete(self, session_id: str) -> bool:
        conn = get_db(self.db_path)
        try:
            cursor = conn.execute("DELETE FROM web_sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_by_user(self, twitch_user_id: str) -> int:
        conn = get_db(self.db_path)
        try:
            cursor = conn.execute(
                "DELETE FROM web_sessions WHERE twitch_user_id = ?", (twitch_user_id,)
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def delete_expired(self) -> int:
        conn = get_db(self.db_path)
        try:
            cursor = conn.execute(
                "DELETE FROM web_sessions WHERE expires_at <= CURRENT_TIMESTAMP"
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()


class OAuthState:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or _get_db_path()

    def create(self, state: str) -> None:
        conn = get_db(self.db_path)
        try:
            conn.execute("INSERT INTO oauth_states (state) VALUES (?)", (state,))
            conn.commit()
        finally:
            conn.close()

    def use(self, state: str) -> bool:
        conn = get_db(self.db_path)
        try:
            row = conn.execute(
                "SELECT * FROM oauth_states WHERE state = ? AND used = 0", (state,)
            ).fetchone()
            if not row:
                return False
            conn.execute("UPDATE oauth_states SET used = 1 WHERE state = ?", (state,))
            conn.commit()
            return True
        finally:
            conn.close()

    def cleanup(self, max_age_seconds: int = 600) -> int:
        conn = get_db(self.db_path)
        try:
            cursor = conn.execute(
                "DELETE FROM oauth_states WHERE used = 1 OR created_at < datetime('now', ?)",
                (f"-{max_age_seconds} seconds",)
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()


class EmailVerification:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or _get_db_path()

    def create(self, twitch_user_id: str, email: str, ttl_seconds: int = 900) -> tuple:
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db(self.db_path)
        try:
            conn.execute(
                "DELETE FROM email_verifications WHERE twitch_user_id = ? AND used = 0",
                (twitch_user_id,)
            )
            conn.execute(
                "INSERT INTO email_verifications (twitch_user_id, email, token_hash, expires_at) VALUES (?, ?, ?, ?)",
                (twitch_user_id, email, token_hash, expires_at)
            )
            conn.commit()
            return token, expires_at
        finally:
            conn.close()

    def consume(self, twitch_user_id: str, token: str) -> bool:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        conn = get_db(self.db_path)
        try:
            row = conn.execute(
                "SELECT * FROM email_verifications WHERE twitch_user_id = ? AND token_hash = ? AND used = 0 AND strftime('%Y-%m-%d %H:%M:%S', expires_at) > strftime('%Y-%m-%d %H:%M:%S', CURRENT_TIMESTAMP)",
                (twitch_user_id, token_hash)
            ).fetchone()
            if not row:
                return False
            conn.execute("UPDATE email_verifications SET used = 1 WHERE id = ?", (row["id"],))
            conn.execute(
                "UPDATE streamers SET email_verified = 1, updated_at = CURRENT_TIMESTAMP WHERE twitch_user_id = ?",
                (twitch_user_id,)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def get_status(self, twitch_user_id: str) -> dict:
        conn = get_db(self.db_path)
        try:
            row = conn.execute(
                "SELECT email, email_verified FROM streamers WHERE twitch_user_id = ?",
                (twitch_user_id,)
            ).fetchone()
            if not row:
                return {"verified": False, "email": None}
            return {"verified": bool(row["email_verified"]), "email": row["email"] or None}
        finally:
            conn.close()

    def cleanup(self) -> int:
        conn = get_db(self.db_path)
        try:
            cursor = conn.execute(
                "DELETE FROM email_verifications WHERE used = 1 OR expires_at <= CURRENT_TIMESTAMP"
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()


class LinkCode:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or _get_db_path()

    def create(self, twitch_user_id: str, ttl_seconds: int = 60) -> tuple:
        code = f"{secrets.randbelow(1000000):06d}"
        salt = secrets.token_hex(16)
        code_hash = hashlib.sha256((salt + code).encode()).hexdigest()
        expires_at = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db(self.db_path)
        try:
            conn.execute(
                "UPDATE link_codes SET used = 1 WHERE twitch_user_id = ? AND used = 0",
                (twitch_user_id,)
            )
            conn.execute(
                "INSERT INTO link_codes (twitch_user_id, code_hash, code_salt, expires_at) VALUES (?, ?, ?, ?)",
                (twitch_user_id, code_hash, salt, expires_at)
            )
            conn.commit()
            return code, expires_at
        finally:
            conn.close()

    def consume(self, twitch_user_id: str, code: str, bridge_instance_id: str = "") -> tuple:
        conn = get_db(self.db_path)
        try:
            row = conn.execute(
                "SELECT * FROM link_codes WHERE twitch_user_id = ? AND used = 0 AND strftime('%Y-%m-%d %H:%M:%S', expires_at) > strftime('%Y-%m-%d %H:%M:%S', CURRENT_TIMESTAMP) ORDER BY created_at DESC LIMIT 1",
                (twitch_user_id,)
            ).fetchone()
            if not row:
                return None, False
            computed_hash = hashlib.sha256((row["code_salt"] + code).encode()).hexdigest()
            if not hmac_mod.compare_digest(computed_hash, row["code_hash"]):
                return None, False
            conn.execute("BEGIN")
            conn.execute("UPDATE link_codes SET used = 1 WHERE id = ?", (row["id"],))
            conn.execute(
                "INSERT OR REPLACE INTO streamer_links (twitch_user_id, bridge_instance_id, link_code_id, status, updated_at) VALUES (?, ?, ?, 'LINKED', CURRENT_TIMESTAMP)",
                (twitch_user_id, bridge_instance_id, row["id"])
            )
            conn.commit()
            return row["id"], True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def cleanup(self) -> int:
        conn = get_db(self.db_path)
        try:
            cursor = conn.execute(
                "DELETE FROM link_codes WHERE used = 1 OR expires_at <= CURRENT_TIMESTAMP"
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()


class StreamerLink:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or _get_db_path()

    def get(self, twitch_user_id: str) -> Optional[dict]:
        conn = get_db(self.db_path)
        try:
            row = conn.execute(
                "SELECT * FROM streamer_links WHERE twitch_user_id = ? AND status = 'LINKED'",
                (twitch_user_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def revoke(self, twitch_user_id: str) -> bool:
        conn = get_db(self.db_path)
        try:
            cursor = conn.execute(
                "UPDATE streamer_links SET status = 'REVOKED', updated_at = CURRENT_TIMESTAMP WHERE twitch_user_id = ? AND status = 'LINKED'",
                (twitch_user_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
