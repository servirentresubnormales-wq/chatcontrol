# ChatControl Core Mock

## What is it

A Python TCP server that mimics the ChatControl Core protocol without executing Minecraft. It allows testing the full Bridge pipeline locally.

## What it simulates

- TCP/JSON protocol v1
- Token-based authentication (auth handshake)
- Request reception and validation
- Success/error responses matching real Core format
- Cooldowns (basic simulation)
- Player lookup ("Streamer" valid, others → PLAYER_NOT_FOUND)
- System enabled/disabled state
- Configurable responses per action

## What it does NOT simulate

- Minecraft world, entities, or blocks
- Actual action execution (zombie spawn, creeper spawn, etc.)
- Thread bridging to server thread
- Complex rate limiting beyond auth
- ActionExecutor, ActionRegistry, SafetyChecker internals

## Quick start

### Run as standalone server

```bash
cd bridge
python -m mocks.core_mock --port 8765 --token MY_SECRET
```

Options:
- `--host` — bind address (default: 127.0.0.1)
- `--port` — bind port (default: 8765)
- `--token` — auth token (default: TEST_TOKEN)
- `--no-auth` — disable authentication
- `--cooldown` — default cooldown in seconds (default: 0)
- `-v` — verbose logging

### Connect the Bridge

Set `config.yaml`:

```yaml
minecraft:
  host: "127.0.0.1"
  port: 8765
  auth_token: "MY_SECRET"
```

Then run the Bridge normally:

```bash
python main.py
```

## Protocol compliance

The mock follows `docs/PROTOCOL.md` exactly:

```
Bridge                              CoreMock
  |                                    |
  |--- TCP connect ------------------>|
  |                                    |
  |--- {"type":"auth",               ->|
  |     "token":"...",                 |
  |     "protocol_version":1}          |
  |                                    |
  |<-- {"type":"auth",  --------------|
  |     "success":true}                |
  |                                    |
  |--- {"action":"zombie",  --------->|
  |     "protocol_version":1}          |
  |                                    |
  |<-- {"success":true,  -------------|
  |     "action":"zombie"}             |
```

## Error codes

Uses the same `ErrorCode` values as the Java Core:

| Code | When |
|------|------|
| `INVALID_JSON` | Malformed JSON or message too large |
| `MISSING_ACTION` | No `action` field |
| `UNKNOWN_ACTION` | Action not in valid set |
| `PLAYER_NOT_FOUND` | Target != "Streamer" |
| `SYSTEM_DISABLED` | System disabled via config |
| `ON_COOLDOWN` | Action on cooldown |
| `UNAUTHORIZED` | Not authenticated or wrong token |
| `INVALID_PROTOCOL` | Wrong protocol_version or wrong message type |
| `EXECUTION_ERROR` | Custom error via `set_action_response()` |

## Programmatic API

```python
from mocks.core_mock import CoreMock

mock = CoreMock(port=18765, auth_token="TEST_TOKEN")
mock.start()

# Configure responses
mock.set_action_response("zombie", success=True, message="Custom message")
mock.set_action_response("creeper", success=False, error="EXECUTION_ERROR")
mock.set_system_enabled(False)  # simulate disabled system
mock.set_default_cooldown(5.0)  # simulate cooldowns

# Get received requests
requests = mock.get_received_requests()

mock.stop()
```

## Running tests

### Unit + integration tests

```bash
cd bridge
python -m pytest tests/test_core_mock.py -v
```

### Quick integration check

```bash
cd bridge
python tests/run_integration.py
```

Expected output:
```
  [PASS] AUTH PASS — correct token
  [PASS] AUTH FAIL — wrong token
  [PASS] REJECT  — action before auth
  [PASS] REQUEST — zombie action
  [PASS] ERROR   — player not found
  [PASS] RECONNECT — server restart
  [PASS] EVENTS  — all 10 event numbers
  [PASS] CHICKENS — rapid fire 5x

  ALL 8 TESTS PASSED
```

## Limitations

1. **No Minecraft** — actions return mock responses, not real game effects
2. **Simple cooldowns** — no per-user cooldown tracking (Bridge handles that)
3. **No rate limiting** — beyond auth failed attempts, no action rate limiting
4. **Single player** — only "Streamer" is recognized as valid
5. **No threading bridge** — responses are immediate (no server thread simulation)

## Architecture

```
bridge/
├── mocks/
│   ├── __init__.py
│   └── core_mock.py          # CoreMock TCP server
├── tests/
│   ├── test_core_mock.py      # 55 tests
│   └── run_integration.py     # Quick integration runner
└── docs/
    └── CORE_MOCK.md           # This file
```

## Replacing with real Core

When you have a real Minecraft host:

1. Stop the Core Mock
2. Start the real ChatControl Core on the same port
3. No Bridge config changes needed (same host, port, token)

The Bridge flow remains identical:

```
Twitch → Bridge → TCP → Auth → [CoreMock or Real Core]
```
