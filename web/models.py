import sqlite3
import os
import json
from typing import Optional

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "chatcontrol.db")


def _get_db_path() -> str:
    return os.environ.get("DB_PATH") or DEFAULT_DB_PATH

DEFAULT_EVENT_CONFIG = {
    1: {"action": "zombie", "enabled": True, "cooldown": 10, "params": {"radius": 4}},
    2: {"action": "spiders", "enabled": True, "cooldown": 15, "params": {"amount": 4, "radius": 5}},
    3: {"action": "slowness", "enabled": True, "cooldown": 20, "params": {"duration": 200, "amplifier": 1}},
    4: {"action": "blindness", "enabled": True, "cooldown": 20, "params": {"duration": 160, "amplifier": 0}},
    5: {"action": "creeper", "enabled": True, "cooldown": 30, "params": {"radius": 4}},
    6: {"action": "storm", "enabled": True, "cooldown": 60, "params": {"duration": 600, "thunder": True}},
    7: {"action": "random_teleport", "enabled": True, "cooldown": 60, "params": {"radius": 30, "max-attempts": 20}},
    8: {"action": "explosion", "enabled": True, "cooldown": 30, "params": {"radius": 3.0, "fire": False, "destroy-blocks": False}},
    9: {"action": "random_event", "enabled": True, "cooldown": 60, "params": {}},
    10: {"action": "chickens", "enabled": True, "cooldown": 0, "params": {"amount": 1, "radius": 4}},
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
    """)
    conn.commit()
    conn.close()


class Streamer:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or _get_db_path()

    def get_or_create(self, twitch_user_id: str, twitch_login: str, display_name: str,
                      access_token: str = None, refresh_token: str = None) -> dict:
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
                    updated_at = CURRENT_TIMESTAMP
                    WHERE twitch_user_id = ?
                """, (twitch_login, display_name, access_token, refresh_token, twitch_user_id))
                conn.commit()
                return dict(existing)
            else:
                conn.execute("""
                    INSERT INTO streamers (twitch_user_id, twitch_login, display_name, access_token, refresh_token)
                    VALUES (?, ?, ?, ?, ?)
                """, (twitch_user_id, twitch_login, display_name, access_token, refresh_token))
                conn.commit()

                for num, cfg in DEFAULT_EVENT_CONFIG.items():
                    conn.execute("""
                        INSERT INTO event_settings (twitch_user_id, event_number, action, enabled, cooldown, params)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (twitch_user_id, num, cfg["action"], cfg["enabled"], cfg["cooldown"],
                          str(__import__('json').dumps(cfg["params"]))))
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
                    updates["enabled"] = 1 if event["enabled"] else 0
                if "cooldown" in event:
                    updates["cooldown"] = event["cooldown"]
                if "params" in event:
                    updates["params"] = str(__import__('json').dumps(event["params"]))
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
