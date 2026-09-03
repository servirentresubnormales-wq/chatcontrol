# Phase 3C Report: Secure Bridge → Core TCP Authentication

## Objective
Implement secure token-based authentication between Python Bridge and Java Core over TCP, preventing unauthorized command execution.

## Implementation

### 1. Java Core — ModConfig.java
Added `AuthenticationConfig` nested class with:
- `enabled` (default: false) — toggle authentication
- `token` (default: "") — shared secret token
- `timeoutSeconds` (default: 10) — auth handshake timeout
- `maxFailedAttempts` (default: 5) — rate limit threshold
- `rateLimitWindowSeconds` (default: 300) — rate limit window

### 2. Java Core — AuthenticationManager.java (NEW)
State machine for per-connection auth:
- States: IDLE → AUTHENTICATING → AUTHENTICATED/REJECTED/CLOSED
- Constant-time token comparison via `MessageDigest.isEqual()`
- Rate limiting: tracks failed attempts per connection ID
- Windowed rate limit (expired attempts are pruned)

### 3. Java Core — CommandReceiver.java
Modified `handleClient()`:
- Generates unique connection ID per client
- Checks rate limiting before accepting auth
- If auth enabled: calls `handleAuthentication()` with timeout
- If auth disabled: skips handshake (backward compatible)
- Commands rejected with `UNAUTHORIZED` if not authenticated
- `handleAuthentication()` reads first line as auth JSON, validates type/token/protocol
- On failure: records failed attempt, sends error response, closes connection

### 4. Python Bridge — protocol.py
Added:
- `serialize_auth_request(token)` — creates auth JSON
- `deserialize_auth_response(raw)` — parses auth response
- `compare_tokens(expected, actual)` — constant-time comparison via `hmac.compare_digest()`

### 5. Python Bridge — client.py
Modified `MinecraftClient`:
- New `authenticate()` method — sends auth handshake after connect
- New `_authenticated` flag — tracks auth state
- `send_request()` rejects if not authenticated
- `disconnect()` and `reconnect()` clear auth state
- If token is empty, `authenticate()` skips handshake (matches Core behavior)

### 6. Python Bridge — main.py
Updated `run_live_loop()`:
- Calls `mc_client.authenticate()` after `connect()`
- Retries on auth failure
- Queue processor checks both `connected` and `authenticated`

## Auth Handshake Protocol

```
Bridge                              Core
  |                                    |
  |--- TCP connect ------------------>|
  |                                    |
  |--- {"type":"auth",               ->|
  |     "token":"secret",              |
  |     "protocol_version":1}          |
  |                                    |
  |<-- {"type":"auth",  --------------|
  |     "success":true,                |
  |     "message":"Authenticated"}     |
  |                                    |
  |--- {"action":"zombie",  --------->|
  |     "protocol_version":1}          |
  |                                    |
  |<-- {"success":true,  -------------|
  |     "action":"zombie"}             |
```

## Configuration

**Java Core (`config/chatcontrol.json`):**
```json
{
  "authentication": {
    "enabled": true,
    "token": "your-secret-token",
    "timeoutSeconds": 10,
    "maxFailedAttempts": 5,
    "rateLimitWindowSeconds": 300
  }
}
```

**Python Bridge (`config.yaml`):**
```yaml
minecraft:
  auth_token: "your-secret-token"
```

## Security Features

| Feature | Implementation |
|---------|---------------|
| Constant-time comparison | Java: `MessageDigest.isEqual()`, Python: `hmac.compare_digest()` |
| Rate limiting | Per-connection ID, windowed (5 attempts / 5 min default) |
| Auth timeout | Configurable (10s default), closes connection on timeout |
| Pre-auth rejection | Commands sent before auth → `UNAUTHORIZED` error |
| Backward compatible | Auth disabled = no handshake required |
| No TLS warning | Documented in PROTOCOL.md |

## Tests

### Java (130 tests, all pass)
- `AuthenticationManagerTest.java` — 17 tests:
  - Token validation (correct/incorrect/null/empty)
  - Disabled auth bypass
  - No-token-config bypass
  - Connection state transitions
  - Rate limiting (below/at/above threshold)
  - Rate limiting disabled
  - Timeout config
  - Constant-time comparison

### Python (334 tests, all pass)
- `test_authenticated_connection.py` — 21 tests:
  - Auth protocol serialization/deserialization (10 tests)
  - Client auth handshake (success/failure/closed/invalid) (5 tests)
  - Auth-gated send_request (3 tests)
  - Config auth_token property (2 tests)
  - Disconnect/reconnect clears auth (2 tests)

## Files Changed/Created

| File | Action |
|------|--------|
| `config/ModConfig.java` | Modified — added AuthenticationConfig |
| `network/AuthenticationManager.java` | Created |
| `network/CommandReceiver.java` | Modified — auth handshake |
| `bridge/minecraft/client.py` | Modified — authenticate() |
| `bridge/core/protocol.py` | Modified — auth helpers |
| `bridge/main.py` | Modified — auth in live loop |
| `tests/AuthenticationManagerTest.java` | Created |
| `tests/test_authenticated_connection.py` | Created |
| `docs/PROTOCOL.md` | Modified — auth section |
| `docs/ARCHITECTURE.md` | Modified — AuthenticationManager |

## Known Limitations

1. **No TLS** — token travels in plaintext TCP. Acceptable for localhost; document for production.
2. **Static token** — no rotation mechanism. Manual config change required.
3. **No certificate pinning** — relies on network-level trust.
4. **Single shared token** — all Bridge instances use same token.

## Test Counts

- **Before**: 269 Python + 113 Java = 382 tests
- **After**: 334 Python + 130 Java = 464 tests
- **Added**: 65 Python + 17 Java = 82 new tests
