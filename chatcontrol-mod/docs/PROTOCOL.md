# ChatControl TCP Protocol

## Version

Current protocol version: **1** (`protocol_version: 1`)

## Connection

- Transport: TCP
- Default port: 8765 (configurable)
- Format: JSON messages, one per line (newline-delimited)
- Encoding: UTF-8

## Authentication

When authentication is enabled in the server config (`authentication.enabled: true`), the Bridge must authenticate before sending any commands.

### Auth Handshake Flow

1. Bridge connects to Core via TCP
2. Bridge sends an `auth` message (first message on the connection)
3. Core validates the token and responds with success or failure
4. If successful, Bridge can send commands
5. If failed, Core closes the connection

### Auth Request (Bridge → Core)

```json
{
  "type": "auth",
  "token": "your-secret-token",
  "protocol_version": 1
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | Must be `"auth"` |
| `token` | string | Yes | Authentication token |
| `protocol_version` | int | Yes | Protocol version (must be 1) |

### Auth Response (Core → Bridge)

**Success:**
```json
{
  "type": "auth",
  "success": true,
  "message": "Authenticated",
  "protocol_version": 1
}
```

**Failure:**
```json
{
  "type": "auth",
  "success": false,
  "error": "UNAUTHORIZED",
  "message": "Invalid token",
  "protocol_version": 1
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"auth"` |
| `success` | boolean | Whether authentication succeeded |
| `message` | string | Human-readable message |
| `error` | string | Error code (on failure) |
| `protocol_version` | int | Protocol version |

### Auth Error Codes

| Code | Description |
|------|-------------|
| `UNAUTHORIZED` | Invalid or missing token |
| `INVALID_PROTOCOL` | Unsupported protocol version |
| `INVALID_JSON` | Malformed auth message |

### Security Notes

- **Token comparison** uses constant-time comparison (`MessageDigest.isEqual` in Java, `hmac.compare_digest` in Python) to prevent timing attacks
- **Rate limiting**: After `maxFailedAttempts` failed auth attempts within `rateLimitWindowSeconds`, new connections from the same source are rejected
- **Auth timeout**: If no auth message is received within `timeoutSeconds`, the connection is closed
- **No TLS**: This authentication does NOT provide encryption. For production use, consider adding TLS or running on a trusted network only

### Auth Configuration

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
  host: "127.0.0.1"
  port: 8765
  auth_token: "your-secret-token"
```

Both sides must use the same token. If authentication is disabled on the server, the Bridge skips the auth handshake entirely.

## Request Format

```json
{
  "action": "zombie",
  "target": "Streamer",
  "source": "twitch",
  "user": "ViewerName",
  "params": {},
  "message_id": "abc123",
  "protocol_version": 1,
  "auth_token": null,
  "metadata": {}
}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `action` | string | Action name to execute |
| `protocol_version` | int | Protocol version (must be 1) |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `target` | string | Minecraft player name (defaults to first online player) |
| `source` | string | Platform source: `twitch`, `youtube`, `console`, `bridge` |
| `user` | string | Username who triggered the action on the platform |
| `params` | object | Action-specific parameters |
| `message_id` | string | Unique message identifier for deduplication |
| `auth_token` | string | Authentication token (reserved for future use) |
| `metadata` | object | Additional metadata (extensible) |

### Backward Compatibility

- `player` is accepted as alias for `target`

## Response Format

### Success

```json
{
  "success": true,
  "action": "zombie",
  "target": "Streamer",
  "message": "Action 'zombie' executed.",
  "execution_time_ms": 45,
  "protocol_version": 1
}
```

### Error

```json
{
  "success": false,
  "error": "PLAYER_NOT_FOUND",
  "message": "Player not found: InvalidPlayer",
  "protocol_version": 1
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether action executed successfully |
| `action` | string | Action that was executed (on success) |
| `target` | string | Target player (on success) |
| `source` | string | Source platform (echoed from request) |
| `user` | string | User who triggered (echoed from request) |
| `message` | string | Human-readable message |
| `error` | string | Error code (on failure) |
| `execution_time_ms` | long | Total processing time |
| `protocol_version` | int | Protocol version |
| `message_id` | string | Message ID (echoed from request) |
| `metadata` | object | Additional data (extensible) |

## Error Codes

| Code | Description |
|------|-------------|
| `INVALID_JSON` | Malformed JSON input |
| `MISSING_ACTION` | Required `action` field absent |
| `UNKNOWN_ACTION` | Action not registered |
| `ACTION_DISABLED` | Action disabled in config |
| `ACTION_BLOCKED` | Action permanently blocked |
| `DANGEROUS_DISABLED` | Dangerous actions disabled in config |
| `PLAYER_NOT_FOUND` | Target player not online |
| `NO_PLAYERS_ONLINE` | No players on server |
| `INVALID_PARAMS` | Parameter validation failed |
| `ON_COOLDOWN` | Per-action cooldown active |
| `RATE_LIMITED` | Rate limit exceeded |
| `GLOBAL_COOLDOWN` | Global cooldown active |
| `SYSTEM_DISABLED` | ChatControl system not active |
| `EXECUTION_ERROR` | Error during action execution |
| `COMMAND_TIMEOUT` | Execution timed out (5s) |
| `THREAD_POOL_FULL` | Server too busy |
| `MISSING_PLAYER` | Command requires a player context |
| `UNAUTHORIZED` | Authentication failed |
| `INVALID_PROTOCOL` | Unsupported protocol version |

## Parameters by Action

### zombie
```json
{"params": {"radius": 4}}
```

### spiders
```json
{"params": {"amount": 4, "radius": 5}}
```

### slowness
```json
{"params": {"duration": 200, "amplifier": 1}}
```

### blindness
```json
{"params": {"duration": 160, "amplifier": 0}}
```

### creeper
```json
{"params": {"radius": 4}}
```

### storm
```json
{"params": {"duration": 600, "thunder": true}}
```

### random_teleport
```json
{"params": {"radius": 30, "max-attempts": 20}}
```

### explosion
```json
{"params": {"radius": 3.0, "fire": false, "destroy-blocks": false}}
```

### random_event
```json
{"params": {"actions": ["zombie", "spiders", "creeper"]}}
```

### chickens
```json
{"params": {"amount": 1, "radius": 4}}
```

### give_item
```json
{"params": {"item": "minecraft:diamond", "count": 1}}
```

### summon_mob
```json
{"params": {"mob": "minecraft:zombie", "count": 1}}
```

### apply_effect
```json
{"params": {"effect": "minecraft:speed", "duration": 200, "amplifier": 0}}
```

## Example Usage

### TCP Client (Python)
```python
import socket
import json

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("localhost", 8765))

request = {
    "action": "zombie",
    "target": "Streamer",
    "source": "twitch",
    "user": "Viewer123",
    "params": {"radius": 4},
    "protocol_version": 1,
    "message_id": "msg_001"
}

sock.sendall((json.dumps(request) + "\n").encode())
response = json.loads(sock.recv(4096).decode())
print(response)
```

### Example Response
```json
{
  "success": true,
  "action": "zombie",
  "target": "Streamer",
  "source": "twitch",
  "user": "Viewer123",
  "message": "Action 'zombie' executed.",
  "execution_time_ms": 45,
  "protocol_version": 1,
  "message_id": "msg_001"
}
```
