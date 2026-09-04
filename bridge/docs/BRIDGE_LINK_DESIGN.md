# Bridge Link Integration — Design Document

## 1. Bridge Instance Identity

### Problem
Multiple Bridge instances can exist (one per streamer). Backend needs to identify *which* Bridge instance is sending heartbeats or completing link flows.

### Solution
- Add `bridge_instance_id` to config, auto-generated at startup if not set.
- Store in `config.yaml` under `bridge.instance_id`.
- Generated with `secrets.token_urlsafe(16)` → 22-char URL-safe token.

### Implementation
**File: `bridge/core/config.py`**
- Add `bridge.instance_id` to `DEFAULT_CONFIG` with value `"auto-generated"`.
- Add `Config.bridge_instance_id` property:
  ```python
  @property
  def bridge_instance_id(self) -> str:
      raw = self._data.get("bridge", {}).get("instance_id", "auto-generated")
      if raw != "auto-generated":
          return raw
      import secrets
      return secrets.token_urlsafe(16)
  ```
- On first use, if value is `"auto-generated"`, generate a new ID, write it back to `config.yaml`, and use it for the lifetime of the process. This makes it persistent across restarts but unique per Bridge instance.

### Config change
```yaml
bridge:
  target_player: "Streamer"
  reconnect_delay: 5
  request_timeout: 5
  instance_id: "auto-generated"  # replaced with real value on first run
```

---

## 2. TCP Message Handling for Link Requests

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

### Implementation
**File: `bridge/minecraft/client.py`**
- Add `handle_incoming_message(raw: str)` method that parses the JSON, checks `type`, and dispatches:
  - `link_request` → calls `LinkHandler.complete_link()`
  - Unknown type → log warning, ignore

- Add a **background reader thread** that continuously reads from the socket and dispatches incoming messages. Currently `MinecraftClient` only reads in response to a sent request. We need a listener loop.

```python
def _reader_loop(self):
    """Background thread: reads from socket and dispatches incoming messages."""
    buffer = b""
    while self._connected:
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
```

**File: `bridge/core/protocol.py`**
- Add `deserialize_link_request(raw: str) -> dict` function
- Add `serialize_link_response(message_id: str, success: bool, message: str) -> str` function

**File: `bridge/core/models.py`**
- Add `LinkRequest` dataclass
- Add `LinkResponse` dataclass

---

## 3. HTTP Calls to Backend for Linking

### New Module: `bridge/backend/client.py`
A lightweight HTTP client for Backend API calls.

```python
class BackendClient:
    def __init__(self, base_url: str, bridge_token: str):
        self._base_url = base_url.rstrip("/")
        self._bridge_token = bridge_token

    def complete_link(self, twitch_user_id: str, link_code: str, 
                      bridge_instance_id: str) -> dict:
        """POST /api/link/complete"""
        ...

    def heartbeat(self, twitch_user_id: str, bridge_instance_id: str,
                  minecraft_connected: bool) -> dict:
        """POST /api/bridge/heartbeat"""
        ...
```

### Link Flow
1. Core sends `link_request` to Bridge via TCP
2. Bridge extracts: `link_code`, `player_name`
3. Bridge needs `twitch_user_id` — this comes from the authenticated Twitch session (see §5)
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

### Backend API: `POST /api/link/complete` (new endpoint)
**File: `web/app.py`**
```python
@app.route("/api/link/complete", methods=["POST"])
@limiter.limit("10/minute")
def api_link_complete():
    data = request.get_json()
    twitch_user_id = data.get("twitch_user_id")
    bridge_token = data.get("bridge_token")
    link_code = data.get("link_code")
    bridge_instance_id = data.get("bridge_instance_id")

    # Validate bridge credentials
    streamer = Streamer()
    if not streamer.authenticate_bridge(twitch_user_id, bridge_token):
        return jsonify({"error": "Invalid bridge credentials"}), 403

    # Validate link code (pending_links table)
    pending = PendingLink().use(link_code, twitch_user_id)
    if not pending:
        return jsonify({"error": "Invalid or expired link code"}), 400

    # Link accounts
    streamer.update_minecraft_player(twitch_user_id, pending["player_name"])

    return jsonify({
        "success": True,
        "message": f"Successfully linked to account: {twitch_user_id}"
    })
```

---

## 4. Heartbeat Enhancement

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
def _heartbeat_loop(backend_client, twitch_user_id, instance_id, mc_client, running_flag):
    while running_flag.is_set():
        try:
            backend_client.heartbeat(
                twitch_user_id=twitch_user_id,
                bridge_instance_id=instance_id,
                minecraft_connected=mc_client.connected and mc_client.authenticated,
            )
        except Exception as e:
            logger.warning("[HEARTBEAT] Failed: %s", e)
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
    # Also store bridge_instance_id and minecraft_connected
    streamer.update_bridge_status(
        twitch_user_id,
        bridge_instance_id=bridge_instance_id,
        minecraft_connected=minecraft_connected,
    )
    return jsonify({"success": True})
```

### Backend DB change
**File: `web/models.py`** — Add `bridge_instance_id` column to streamers table:
```sql
ALTER TABLE streamers ADD COLUMN bridge_instance_id TEXT;
```

---

## 5. State Management

### Bridge Internal State
**New file: `bridge/core/state.py`**
```python
class BridgeState:
    def __init__(self):
        self.twitch_user_id: str | None = None
        self.bridge_token: str | None = None
        self.bridge_instance_id: str | None = None
        self.linked: bool = False
        self.minecraft_connected: bool = False

    def update_from_twitch_auth(self, auth: TwitchAuth):
        self.twitch_user_id = auth.user_id

    def update_from_config(self, config: Config):
        self.bridge_token = config.bridge_token  # needs new config field
        self.bridge_instance_id = config.bridge_instance_id
```

### Config additions
**File: `bridge/core/config.py`** — Add `bridge_token` to config:
```yaml
bridge:
  bridge_token: ""  # obtained from Backend via /api/bridge/register
```

The `bridge_token` is obtained by the streamer through the web UI (`POST /api/bridge/register`) and placed into `config.yaml`. This is the authentication mechanism.

### Link State
- Before linking: `BridgeState.linked = False`
- After successful `POST /api/link/complete`: `BridgeState.linked = True`
- Stored in-memory only (not persisted). If Bridge restarts, heartbeat re-establishes connection.

---

## 6. Error Handling

| Error | Handling |
|-------|----------|
| Core sends `link_request` but Bridge not linked to Twitch | Send `link_response` with `success=false`, message "Bridge not linked to Twitch" |
| Backend HTTP call fails (network) | Retry once after 2s, then send failure response to Core |
| Backend returns 403 (invalid token) | Log error, send failure response to Core |
| Backend returns 400 (invalid/expired code) | Send failure response to Core with error message |
| TCP connection lost during link flow | Log warning, discard in-flight link request |
| Heartbeat fails | Log warning, continue. Backend marks bridge disconnected after timeout |
| Config missing `bridge_token` | Log error at startup, disable link functionality |

### Timeout
- Backend HTTP calls: 5s timeout (configurable)
- Link flow total: Core should have its own timeout (e.g., 10s) before telling player "Link timed out"

---

## 7. File Locations for Changes

### Bridge (Python)
| File | Change |
|------|--------|
| `bridge/core/config.py` | Add `bridge.instance_id`, `bridge.bridge_token` to defaults; add properties |
| `bridge/core/models.py` | Add `LinkRequest`, `LinkResponse` dataclasses |
| `bridge/core/protocol.py` | Add `deserialize_link_request()`, `serialize_link_response()` |
| `bridge/core/state.py` | **NEW** — `BridgeState` class |
| `bridge/minecraft/client.py` | Add background reader thread, `_handle_incoming()` dispatch |
| `bridge/backend/client.py` | **NEW** — `BackendClient` HTTP class |
| `bridge/main.py` | Instantiate `BackendClient`, `BridgeState`; start heartbeat thread; wire link handler |
| `bridge/config.yaml` | Add `bridge.instance_id`, `bridge.bridge_token` |
| `bridge/config.example.yaml` | Update example with new fields |

### Backend (Python/Flask)
| File | Change |
|------|--------|
| `web/app.py` | Add `POST /api/link/complete` endpoint; enhance heartbeat endpoint |
| `web/models.py` | Add `bridge_instance_id` column; add `PendingLink` model; add `update_bridge_status()` |

---

## 8. Dependencies on Backend and Core

### Backend must provide:
1. **`POST /api/link/complete`** endpoint — validates link code, links Minecraft player to Twitch account
2. **`pending_links` table** — stores codes generated by web UI, with `player_name`, `twitch_user_id`, `code`, `expires_at`
3. **`bridge_instance_id` column** on `streamers` table — stored from heartbeat
4. Enhanced **heartbeat endpoint** that accepts `bridge_instance_id` and `minecraft_connected`

### Core must provide:
1. **`link_request` TCP message** — when player types `/chatcontrol link <code>`, Core sends this to Bridge
2. **Handle `link_response`** — Core receives Bridge's response and displays it to the player
3. Core already has the `/chatcontrol link <code>` command handler (assumed to exist)

### Bridge must provide:
1. **Background reader thread** — listens for incoming TCP messages from Core
2. **Backend HTTP client** — calls Backend API
3. **`bridge_instance_id`** — unique identifier
4. **Heartbeat thread** — periodic pings to Backend

---

## 9. Complete Link Flow (Sequence)

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

## 10. Implementation Order

1. **Phase 1 — Identity**: Add `bridge_instance_id` to config and `BridgeState`
2. **Phase 2 — Backend Client**: Create `bridge/backend/client.py` with `complete_link()` and `heartbeat()`
3. **Phase 3 — Protocol Extension**: Add `link_request`/`link_response` to protocol and models
4. **Phase 4 — Reader Thread**: Add background TCP reader to `MinecraftClient`
5. **Phase 5 — Link Handler**: Wire `link_request` → `BackendClient.complete_link()` → `link_response`
6. **Phase 6 — Heartbeat**: Add heartbeat thread to `main.py`, enhance Backend endpoint
7. **Phase 7 — Backend API**: Add `/api/link/complete` endpoint and `PendingLink` model
