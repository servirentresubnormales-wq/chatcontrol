# Bridge Email+Link Integration — Complete Design Document

## 1. Bridge Identity Design

### Problem
Multiple Bridge instances can exist (one per streamer). Backend needs to identify *which* Bridge instance is sending heartbeats or completing link flows.

### Solution
- Add `bridge_instance_id` to config, auto-generated at startup if not set.
- Store in `config.yaml` under `bridge.instance_id`.
- Generated with `secrets.token_urlsafe(16)` → 22-char URL-safe token.

### Implementation
**File: `bridge/core/config.py`**

```python
import secrets

DEFAULT_CONFIG = {
    "bridge": {
        "target_player": "Streamer",
        "reconnect_delay": 5,
        "request_timeout": 5,
        "instance_id": "auto-generated",
        "bridge_token": "",
        "backend_url": "http://localhost:5000",
    },
    # ... rest of config
}

class Config:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data
        self._instance_id: str | None = None  # cached generated ID

    @property
    def bridge_instance_id(self) -> str:
        raw = self._data.get("bridge", {}).get("instance_id", "auto-generated")
        if raw != "auto-generated":
            return raw
        
        # Generate and cache on first access
        if self._instance_id is None:
            self._instance_id = secrets.token_urlsafe(16)
        return self._instance_id

    @property
    def bridge_token(self) -> str:
        return self._data.get("bridge", {}).get("bridge_token", "")

    @property
    def backend_url(self) -> str:
        return self._data.get("bridge", {}).get("backend_url", "http://localhost:5000")

    def persist_instance_id(self, config_path: str = "config.yaml") -> None:
        """Write the generated instance_id back to config.yaml."""
        import re
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            if self._instance_id:
                # Replace the placeholder with actual generated ID
                content = re.sub(
                    r'instance_id:\s*"auto-generated"',
                    f'instance_id: "{self._instance_id}"',
                    content,
                )
                with open(config_path, "w", encoding="utf-8") as f:
                    f.write(content)
        except Exception as e:
            logger.warning("Could not persist instance_id: %s", e)
```

### Config change
```yaml
bridge:
  target_player: "Streamer"
  reconnect_delay: 5
  request_timeout: 5
  instance_id: "auto-generated"  # replaced with real value on first run
  bridge_token: ""  # obtained from Backend via /api/bridge/register
  backend_url: "http://localhost:5000"
```

---

## 2. Config Changes

### New config fields
```yaml
bridge:
  instance_id: "auto-generated"  # Bridge instance identifier
  bridge_token: ""               # Authentication token from Backend
  backend_url: "http://localhost:5000"  # Backend API base URL
```

### Config class updates
**File: `bridge/core/config.py`**

Add properties:
- `bridge_instance_id` → returns instance_id (generates if auto-generated)
- `bridge_token` → returns bridge authentication token
- `backend_url` → returns Backend API base URL
- `persist_instance_id()` → writes generated ID back to config.yaml

---

## 3. TCP Message Handling

### Current TCP Protocol
- Bridge → Core: `BridgeRequest` JSON (action, target, source, user, params, etc.)
- Core → Bridge: `BridgeResponse` JSON (success, message, error, etc.)
- Bridge currently only *sends* requests and *receives* responses.

### New: Core → Bridge Push Messages
When a Minecraft player types `/chatcontrol link <code>`, Core needs to push a message to Bridge. This requires a **new TCP message type** in the protocol.

#### Protocol Extension
Add a `type` field to distinguish message types. Currently messages are implicit `request`/`response`. New types:

| Direction | Type | Purpose |
|-----------|------|---------|
| Core → Bridge | `link_request` | Player initiated link, Core forwards code |
| Bridge → Core | `link_response` | Link result (success or failure) |
| Core → Bridge | `unlink_request` | Player initiated unlink |
| Bridge → Core | `unlink_response` | Unlink result |

**Core → Bridge (link_request):**
```json
{
  "type": "link_request",
  "link_code": "AbC123",
  "player_name": "Steve",
  "message_id": "uuid-hex"
}
```

**Bridge → Core (link_response):**
```json
{
  "type": "link_response",
  "message_id": "uuid-hex",
  "success": true,
  "message": "Successfully linked to account: MyStreamer"
}
```

**Core → Bridge (unlink_request):**
```json
{
  "type": "unlink_request",
  "player_name": "Steve",
  "message_id": "uuid-hex"
}
```

**Bridge → Core (unlink_response):**
```json
{
  "type": "unlink_response",
  "message_id": "uuid-hex",
  "success": true,
  "message": "Successfully unlinked"
}
```

### Implementation
**File: `bridge/minecraft/client.py`**

Add background reader thread and message dispatch:

```python
import threading
from typing import Callable

class MinecraftClient:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._sock: socket.socket | None = None
        self._lock = threading.Lock()
        self._connected = False
        self._authenticated = False
        self._reader_thread: threading.Thread | None = None
        self._message_handlers: dict[str, Callable] = {}
        self._running = False

    def register_handler(self, message_type: str, handler: Callable) -> None:
        """Register a handler for incoming TCP messages of a given type."""
        self._message_handlers[message_type] = handler

    def _start_reader(self) -> None:
        """Start background reader thread."""
        self._running = True
        self._reader_thread = threading.Thread(
            target=self._reader_loop,
            name="TCPReader",
            daemon=True,
        )
        self._reader_thread.start()

    def _reader_loop(self) -> None:
        """Background thread: reads from socket and dispatches incoming messages."""
        buffer = b""
        while self._running and self._connected:
            try:
                data = self._sock.recv(65536)
                if not data:
                    break
                buffer += data
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    raw = line.decode("utf-8").strip()
                    if raw:
                        self._handle_incoming(raw)
            except OSError:
                break
        self._connected = False

    def _handle_incoming(self, raw: str) -> None:
        """Parse and dispatch incoming TCP message."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("[TCP] Invalid JSON received: %s", raw[:100])
            return

        msg_type = data.get("type", "")
        handler = self._message_handlers.get(msg_type)
        if handler:
            try:
                handler(data)
            except Exception as e:
                logger.error("[TCP] Handler error for %s: %s", msg_type, e)
        else:
            logger.debug("[TCP] Unknown message type: %s", msg_type)

    def connect(self) -> None:
        with self._lock:
            if self._connected:
                return
            try:
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._sock.settimeout(self._config.request_timeout)
                self._sock.connect((self._config.host, self._config.port))
                self._connected = True
                self._start_reader()  # Start reader thread
                logger.info("[INFO] Connected to Minecraft Core at %s:%d",
                          self._config.host, self._config.port)
            except OSError as e:
                self._connected = False
                raise ConnectionError(f"Failed to connect: {e}") from e

    def disconnect(self) -> None:
        self._running = False
        with self._lock:
            self._connected = False
            self._authenticated = False
            if self._sock:
                try:
                    self._sock.close()
                except OSError:
                    pass
                self._sock = None
            logger.info("[INFO] Disconnected from Minecraft Core")
```

**File: `bridge/core/protocol.py`**

Add new serialization/deserialization functions:

```python
def deserialize_link_request(raw: str) -> dict[str, Any]:
    """Deserialize a link_request message from Core."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ProtocolError(f"Invalid JSON link_request: {e}") from e

    if data.get("type") != "link_request":
        raise ProtocolError(f"Expected link_request, got type: {data.get('type')}")

    if "link_code" not in data:
        raise ProtocolError("link_request missing link_code")

    return data


def serialize_link_response(message_id: str, success: bool, message: str) -> str:
    """Serialize a link_response message to Core."""
    return json.dumps({
        "type": "link_response",
        "message_id": message_id,
        "success": success,
        "message": message,
    }, ensure_ascii=False)


def deserialize_unlink_request(raw: str) -> dict[str, Any]:
    """Deserialize an unlink_request message from Core."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ProtocolError(f"Invalid JSON unlink_request: {e}") from e

    if data.get("type") != "unlink_request":
        raise ProtocolError(f"Expected unlink_request, got type: {data.get('type')}")

    return data


def serialize_unlink_response(message_id: str, success: bool, message: str) -> str:
    """Serialize an unlink_response message to Core."""
    return json.dumps({
        "type": "unlink_response",
        "message_id": message_id,
        "success": success,
        "message": message,
    }, ensure_ascii=False)
```

**File: `bridge/core/models.py`**

Add new dataclasses:

```python
@dataclass
class LinkRequest:
    link_code: str
    player_name: str
    message_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LinkRequest:
        return cls(
            link_code=data["link_code"],
            player_name=data.get("player_name", ""),
            message_id=data.get("message_id", uuid.uuid4().hex),
        )


@dataclass
class LinkResponse:
    success: bool
    message: str
    message_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "link_response",
            "message_id": self.message_id,
            "success": self.success,
            "message": self.message,
        }


@dataclass
class UnlinkRequest:
    player_name: str
    message_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UnlinkRequest:
        return cls(
            player_name=data.get("player_name", ""),
            message_id=data.get("message_id", uuid.uuid4().hex),
        )


@dataclass
class UnlinkResponse:
    success: bool
    message: str
    message_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "unlink_response",
            "message_id": self.message_id,
            "success": self.success,
            "message": self.message,
        }
```

---

## 4. HTTP Calls to Backend

### New Module: `bridge/backend/client.py`

```python
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


class BackendClient:
    """HTTP client for ChatControl Backend API."""

    def __init__(self, base_url: str, bridge_token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._bridge_token = bridge_token
        self._timeout = 10

    def _request(self, method: str, path: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make an HTTP request to the Backend API."""
        url = f"{self._base_url}{path}"
        body = json.dumps(data).encode("utf-8") if data else None

        req = urllib.request.Request(url, data=body, method=method)
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self._bridge_token}")

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")
            logger.error("[BACKEND] HTTP %d: %s", e.code, body_text)
            raise BackendError(f"HTTP {e.code}: {body_text}") from e
        except (OSError, json.JSONDecodeError) as e:
            logger.error("[BACKEND] Request failed: %s", e)
            raise BackendError(f"Request failed: {e}") from e

    def heartbeat(
        self,
        twitch_user_id: str,
        bridge_instance_id: str,
        minecraft_connected: bool,
    ) -> dict[str, Any]:
        """POST /api/bridge/heartbeat"""
        return self._request("POST", "/api/bridge/heartbeat", {
            "twitch_user_id": twitch_user_id,
            "bridge_token": self._bridge_token,
            "bridge_instance_id": bridge_instance_id,
            "minecraft_connected": minecraft_connected,
        })

    def complete_link(
        self,
        twitch_user_id: str,
        link_code: str,
        bridge_instance_id: str,
    ) -> dict[str, Any]:
        """POST /api/link/complete"""
        return self._request("POST", "/api/link/complete", {
            "twitch_user_id": twitch_user_id,
            "bridge_token": self._bridge_token,
            "link_code": link_code,
            "bridge_instance_id": bridge_instance_id,
        })

    def revoke_link(self, twitch_user_id: str) -> dict[str, Any]:
        """POST /api/link/revoke"""
        return self._request("POST", "/api/link/revoke", {
            "twitch_user_id": twitch_user_id,
            "bridge_token": self._bridge_token,
        })


class BackendError(Exception):
    """Error communicating with Backend API."""
    pass
```

### Link Flow
1. Core sends `link_request` to Bridge via TCP
2. Bridge extracts: `link_code`, `player_name`
3. Bridge needs `twitch_user_id` — this comes from the authenticated Twitch session
4. Bridge calls `BackendClient.complete_link()`:
   ```
   POST /api/link/complete
   {
     "twitch_user_id": "...",
     "bridge_token": "...",
     "link_code": "AbC123",
     "bridge_instance_id": "..."
   }
   ```
5. Backend validates code against pending links in DB, links accounts
6. Backend returns: `{"success": true, "message": "Linked to: MyStreamer"}`
7. Bridge sends `link_response` back to Core via TCP
8. Core displays result to the player in chat

### Unlink Flow
1. Core sends `unlink_request` to Bridge via TCP
2. Bridge calls `BackendClient.revoke_link()`:
   ```
   POST /api/link/revoke
   {
     "twitch_user_id": "...",
     "bridge_token": "..."
   }
   ```
3. Backend revokes link in DB
4. Backend returns: `{"success": true, "message": "Unlinked"}`
5. Bridge sends `unlink_response` back to Core via TCP
6. Core displays result to the player in chat

---

## 5. Heartbeat Enhancement

### Current Behavior
No heartbeat exists in the Bridge codebase yet. The Backend has `POST /api/bridge/heartbeat` that expects:
```json
{"twitch_user_id": "...", "bridge_token": "..."}
```
And sets `bridge_connected = 1`, `last_heartbeat = CURRENT_TIMESTAMP`.

### Enhanced Heartbeat
**File: `bridge/backend/client.py`** — `heartbeat()` method

**File: `bridge/main.py`** — Add heartbeat thread in `run_live_loop()`:

```python
def _heartbeat_loop(
    backend_client: BackendClient,
    twitch_user_id: str,
    instance_id: str,
    mc_client: MinecraftClient,
    running_flag: threading.Event,
) -> None:
    """Background thread: sends periodic heartbeats to Backend."""
    while running_flag.is_set():
        try:
            backend_client.heartbeat(
                twitch_user_id=twitch_user_id,
                bridge_instance_id=instance_id,
                minecraft_connected=mc_client.connected and mc_client.authenticated,
            )
        except BackendError as e:
            logger.warning("[HEARTBEAT] Failed: %s", e)
        except Exception as e:
            logger.error("[HEARTBEAT] Unexpected error: %s", e)
        time.sleep(30)  # every 30 seconds
```

### Enhanced Backend Endpoint
**File: `web/app.py`** — Update `api_bridge_heartbeat`:

```python
@app.route("/api/bridge/heartbeat", methods=["POST"])
def api_bridge_heartbeat():
    data = request.get_json()
    twitch_user_id = data.get("twitch_user_id")
    bridge_token = data.get("bridge_token")
    bridge_instance_id = data.get("bridge_instance_id")
    minecraft_connected = data.get("minecraft_connected", False)

    streamer = Streamer()
    if not streamer.authenticate_bridge(twitch_user_id, bridge_token):
        return jsonify({"error": "Invalid bridge credentials"}), 403

    streamer.update_heartbeat(twitch_user_id)
    streamer.update_bridge_status(
        twitch_user_id,
        bridge_instance_id=bridge_instance_id,
        minecraft_connected=minecraft_connected,
    )
    return jsonify({"success": True})
```

### Backend DB change
**File: `web/models.py`** — Add column to streamers table:
```sql
ALTER TABLE streamers ADD COLUMN bridge_instance_id TEXT;
```

Note: `minecraft_connected`, `last_heartbeat`, `bridge_connected`, and `bridge_token` columns already exist in the schema.

---

## 6. State Management

### Bridge Internal State
**New file: `bridge/core/state.py`**

```python
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BridgeState:
    """Tracks Bridge operational state."""
    
    # Identity
    twitch_user_id: str | None = None
    bridge_token: str | None = None
    bridge_instance_id: str | None = None
    
    # Connection status
    linked: bool = False
    minecraft_connected: bool = False
    backend_reachable: bool = False

    # Pending operations
    pending_link_code: str | None = None
    pending_link_message_id: str | None = None

    def update_from_twitch_auth(self, user_id: str) -> None:
        """Update twitch_user_id from Twitch auth."""
        self.twitch_user_id = user_id
        logger.info("[STATE] Twitch user ID set: %s", user_id)

    def update_from_config(self, config: Any) -> None:
        """Update identity fields from config."""
        self.bridge_token = config.bridge_token
        self.bridge_instance_id = config.bridge_instance_id

    def mark_linked(self) -> None:
        """Mark as successfully linked."""
        self.linked = True
        self.pending_link_code = None
        self.pending_link_message_id = None
        logger.info("[STATE] Bridge marked as linked")

    def mark_unlinked(self) -> None:
        """Mark as unlinked."""
        self.linked = False
        logger.info("[STATE] Bridge marked as unlinked")

    def update_minecraft_status(self, connected: bool) -> None:
        """Update Minecraft connection status."""
        self.minecraft_connected = connected
        logger.debug("[STATE] Minecraft connected: %s", connected)

    def start_link_request(self, link_code: str, message_id: str) -> None:
        """Track pending link request."""
        self.pending_link_code = link_code
        self.pending_link_message_id = message_id
        logger.info("[STATE] Pending link request: code=%s", link_code)

    def clear_pending_link(self) -> None:
        """Clear pending link request."""
        self.pending_link_code = None
        self.pending_link_message_id = None
```

### Config additions
**File: `bridge/core/config.py`** — Add fields to DEFAULT_CONFIG:
```python
DEFAULT_CONFIG = {
    "bridge": {
        "target_player": "Streamer",
        "reconnect_delay": 5,
        "request_timeout": 5,
        "instance_id": "auto-generated",
        "bridge_token": "",
        "backend_url": "http://localhost:5000",
    },
    # ... rest of config
}
```

### Link State
- Before linking: `BridgeState.linked = False`
- After successful `POST /api/link/complete`: `BridgeState.linked = True`
- Stored in-memory only (not persisted). If Bridge restarts, heartbeat re-establishes connection.

---

## 7. Error Handling

| Error | Handling |
|-------|----------|
| Core sends `link_request` but Bridge not linked to Twitch | Send `link_response` with `success=false`, message "Bridge not linked to Twitch" |
| Core sends `link_request` but no `bridge_token` configured | Send `link_response` with `success=false`, message "Bridge not configured" |
| Backend HTTP call fails (network) | Retry once after 2s, then send failure response to Core |
| Backend returns 403 (invalid token) | Log error, send failure response to Core |
| Backend returns 400 (invalid/expired code) | Send failure response to Core with error message |
| TCP connection lost during link flow | Log warning, discard in-flight link request |
| Heartbeat fails | Log warning, continue. Backend marks bridge disconnected after timeout |
| Config missing `bridge_token` | Log error at startup, disable link functionality |
| Link request already pending | Reject new request with "Link already in progress" |

### Timeout
- Backend HTTP calls: 10s timeout (configurable via `_timeout`)
- Link flow total: Core should have its own timeout (e.g., 10s) before telling player "Link timed out"
- Heartbeat interval: 30s
- Heartbeat timeout: Backend marks bridge disconnected after 90s (3 missed heartbeats)

### Error Response Messages
```python
# Standard error responses for link/unlink
LINK_NOT_CONFIGURED = "Bridge not configured for linking"
LINK_NOT_LINKED = "Bridge not linked to Twitch"
LINK_IN_PROGRESS = "Link already in progress"
LINK_FAILED = "Link failed: {}"
LINK_TIMEOUT = "Link request timed out"
UNLINK_FAILED = "Unlink failed: {}"
```

---

## 8. File Locations

### Bridge (Python)
| File | Change |
|------|--------|
| `bridge/core/config.py` | Add `bridge.instance_id`, `bridge.bridge_token`, `bridge.backend_url` to defaults; add properties; add `persist_instance_id()` |
| `bridge/core/models.py` | Add `LinkRequest`, `LinkResponse`, `UnlinkRequest`, `UnlinkResponse` dataclasses |
| `bridge/core/protocol.py` | Add `deserialize_link_request()`, `serialize_link_response()`, `deserialize_unlink_request()`, `serialize_unlink_response()` |
| `bridge/core/state.py` | **NEW** — `BridgeState` class |
| `bridge/minecraft/client.py` | Add background reader thread, `_handle_incoming()` dispatch, `register_handler()` |
| `bridge/backend/__init__.py` | **NEW** — Empty init file |
| `bridge/backend/client.py` | **NEW** — `BackendClient` HTTP class, `BackendError` exception |
| `bridge/main.py` | Instantiate `BackendClient`, `BridgeState`; start heartbeat thread; wire link/unlink handlers |
| `bridge/config.yaml` | Add `bridge.instance_id`, `bridge.bridge_token`, `bridge.backend_url` |
| `bridge/config.example.yaml` | Update example with new fields |

### Backend (Python/Flask)
| File | Change |
|------|--------|
| `web/app.py` | Add `POST /api/link/complete` endpoint; add `POST /api/link/revoke` endpoint; enhance heartbeat endpoint to accept `bridge_instance_id` and `minecraft_connected` |
| `web/models.py` | Add `bridge_instance_id` column; add `PendingLink` model; add `update_bridge_status()` method |

---

## 9. Dependencies

### Backend must provide:
1. **`POST /api/link/complete`** endpoint — validates link code, links Minecraft player to Twitch account
2. **`POST /api/link/revoke`** endpoint — revokes link between Minecraft player and Twitch account
3. **`pending_links` table** — stores codes generated by web UI, with `player_name`, `twitch_user_id`, `code`, `expires_at`
4. **`bridge_instance_id` column** on `streamers` table — stored from heartbeat
5. Enhanced **heartbeat endpoint** that accepts `bridge_instance_id` and `minecraft_connected`

### Already exists in Backend:
- `authenticate_bridge()` method — validates `twitch_user_id` + `bridge_token` pair
- `update_heartbeat()` method — updates `last_heartbeat` and `bridge_connected`
- `bridge_connected`, `minecraft_connected`, `last_heartbeat`, `bridge_token` columns on `streamers` table
- `POST /api/bridge/heartbeat` endpoint
- `POST /api/bridge/register` endpoint

### Core must provide:
1. **`link_request` TCP message** — when player types `/chatcontrol link <code>`, Core sends this to Bridge
2. **Handle `link_response`** — Core receives Bridge's response and displays it to the player
3. **`unlink_request` TCP message** — when player types `/chatcontrol unlink`, Core sends this to Bridge
4. **Handle `unlink_response`** — Core receives Bridge's response and displays it to the player
5. Core already has the `/chatcontrol link <code>` command handler (assumed to exist)

### Bridge must provide:
1. **Background reader thread** — listens for incoming TCP messages from Core
2. **Backend HTTP client** — calls Backend API
3. **`bridge_instance_id`** — unique identifier, persisted across restarts
4. **Heartbeat thread** — periodic pings to Backend
5. **Link/Unlink handlers** — process TCP messages and call Backend API

---

## 10. Complete Link Flow (Sequence)

```
Player (Minecraft)          Core (Java)              Bridge (Python)           Backend (Flask)
       |                        |                        |                        |
       |-- /chatcontrol link AbC123 -->                  |                        |
       |                        |-- link_request -------->                        |
       |                        |   {link_code:"AbC123"} |                        |
       |                        |                        |-- POST /api/link/complete -->
       |                        |                        |   {twitch_user_id,      |
       |                        |                        |    bridge_token,        |
       |                        |                        |    link_code:"AbC123",  |
       |                        |                        |    bridge_instance_id}  |
       |                        |                        |                        |
       |                        |                        |   <-- {success:true,   |
       |                        |                        |      message:"Linked"}  |
       |                        |                        |                        |
       |                        |<-- link_response ------|                        |
       |                        |   {success:true,       |                        |
       |                        |    message:"Linked"}   |                        |
       |<-- "Successfully" -----|                        |                        |
       |    linked!             |                        |                        |
```

---

## 11. Complete Unlink Flow (Sequence)

```
Player (Minecraft)          Core (Java)              Bridge (Python)           Backend (Flask)
       |                        |                        |                        |
       |-- /chatcontrol unlink ->                        |                        |
       |                        |-- unlink_request ------>                        |
       |                        |   {player_name:"Steve"}|                        |
       |                        |                        |-- POST /api/link/revoke -->
       |                        |                        |   {twitch_user_id,      |
       |                        |                        |    bridge_token}        |
       |                        |                        |                        |
       |                        |                        |   <-- {success:true,   |
       |                        |                        |      message:"Unlinked"}|
       |                        |                        |                        |
       |                        |<-- unlink_response ----|                        |
       |                        |   {success:true,       |                        |
       |                        |    message:"Unlinked"} |                        |
       |<-- "Successfully" -----|                        |                        |
       |    unlinked!           |                        |                        |
```

---

## 12. Heartbeat Flow (Sequence)

```
Bridge (Python)                    Backend (Flask)
       |                                |
       |-- POST /api/bridge/heartbeat -->
       |   {twitch_user_id,             |
       |    bridge_token,               |
       |    bridge_instance_id,         |
       |    minecraft_connected}        |
       |                                |
       |<-- {success:true} -------------|
       |                                |
       |   [wait 30s]                   |
       |                                |
       |-- POST /api/bridge/heartbeat -->
       |   {twitch_user_id,             |
       |    bridge_token,               |
       |    bridge_instance_id,         |
       |    minecraft_connected}        |
       |                                |
       |<-- {success:true} -------------|
```

---

## 13. Implementation Order

1. **Phase 1 — Identity**: Add `bridge_instance_id` to config and `BridgeState`
2. **Phase 2 — Backend Client**: Create `bridge/backend/client.py` with `complete_link()`, `revoke_link()`, and `heartbeat()`
3. **Phase 3 — Protocol Extension**: Add `link_request`/`link_response` and `unlink_request`/`unlink_response` to protocol and models
4. **Phase 4 — Reader Thread**: Add background TCP reader to `MinecraftClient`
5. **Phase 5 — Link Handler**: Wire `link_request` → `BackendClient.complete_link()` → `link_response`
6. **Phase 6 — Unlink Handler**: Wire `unlink_request` → `BackendClient.revoke_link()` → `unlink_response`
7. **Phase 7 — Heartbeat**: Add heartbeat thread to `main.py`, enhance Backend endpoint
8. **Phase 8 — Backend API**: Add `/api/link/complete`, `/api/link/revoke` endpoints and `PendingLink` model

---

## 14. Testing Strategy

### Unit Tests
- `test_bridge_state.py` — Test `BridgeState` transitions
- `test_backend_client.py` — Mock HTTP responses, test error handling
- `test_protocol_link.py` — Test serialization/deserialization of link/unlink messages

### Integration Tests
- `test_link_flow.py` — End-to-end test with mocked Backend
- `test_heartbeat.py` — Test heartbeat thread with mocked Backend
- `test_error_handling.py` — Test various failure scenarios

### Manual Testing
1. Start Bridge with mock mode
2. Verify `bridge_instance_id` is generated and persisted
3. Verify heartbeat sends correct payload
4. Simulate link request from Core
5. Verify link response is sent back
6. Test error cases (invalid token, expired code, etc.)
