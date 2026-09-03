# Twitch Integration

Twitch EventSub WebSocket integration for ChatControl Bridge.

## Requirements

- Python 3.12+
- Twitch Developer Application (client_id + client_secret)
- User Access Token with `user:read:chat` scope
- Broadcaster's numeric user ID

## How It Works

```
Twitch Chat → EventSub WebSocket → ChatMessage → CommandParser → CooldownManager → CommandBuilder → MinecraftClient → Core
```

1. Connects to `wss://eventsub.wss.twitch.tv/ws`
2. Receives `session_welcome` with session ID
3. Subscribes to `channel.chat.message` within 10 seconds
4. Converts Twitch events to normalized `ChatMessage`
5. Parses commands (`!zombie`, `!pollos`, or event numbers `1`-`10`)
6. Applies cooldowns before sending to Minecraft Core

## Configuration

Add to `config.yaml`:

```yaml
twitch:
  enabled: true
  client_id: "your_client_id"
  client_secret: ""                    # Not needed for User Access Token
  access_token: "your_user_access_token"
  refresh_token: ""                    # Optional: for automatic token refresh
  broadcaster_id: "12345678"           # Numeric user ID of the channel
  bot_user_id: ""                      # Optional: only if using separate bot account
  channel: "YourChannel"              # Display name for logging
```

### Required Fields (when enabled=true)

| Field | Description |
|-------|-------------|
| `client_id` | Twitch Application Client ID from Developer Console |
| `access_token` | User Access Token with `user:read:chat` scope |
| `broadcaster_id` | Numeric user ID of the channel to monitor |
| `channel` | Display name of the broadcaster |

### Optional Fields

| Field | Description |
|-------|-------------|
| `client_secret` | Only needed for App Access Token flow (not used here) |
| `refresh_token` | For automatic token refresh when token expires |
| `bot_user_id` | Only needed if using a separate bot account |

## Getting Credentials

### 1. Register Application

1. Go to https://dev.twitch.tv/console/apps
2. Register a new application
3. Set OAuth Redirect URL to `http://localhost` (for device code flow)
4. Note your Client ID and Client Secret

### 2. Get User Access Token

EventSub WebSocket **requires** a User Access Token (not App Access Token).

**Scopes needed:** `user:read:chat`

Use one of these flows:
- **Authorization Code Grant**: https://dev.twitch.tv/docs/authentication/getting-tokens-oauth/#authorization-code-grant-flow
- **Device Code Grant**: https://dev.twitch.tv/docs/authentication/getting-tokens-oauth/#device-code-grant-flow

### 3. Get Broadcaster User ID

```
GET https://api.twitch.tv/helix/users?login=YourChannel
```

The broadcaster's numeric user ID is in the `id` field of the response.

### 4. Important: Who is the Token For?

There are two scenarios:

**Scenario A: Single account (broadcaster runs the bot)**
- The access token belongs to the broadcaster
- `broadcaster_id` = the broadcaster's user ID
- `bot_user_id` = empty (same as broadcaster)
- The broadcaster authorizes their OWN application with `user:read:chat`

**Scenario B: Separate bot account**
- The access token belongs to the bot account
- `broadcaster_id` = the channel owner's user ID
- `bot_user_id` = the bot account's user ID
- The bot account authorizes the application with `user:read:chat`
- The broadcaster grants the bot `channel:bot` scope

## EventSub Lifecycle

Based on official Twitch documentation.

### Session Flow
1. Connect to `wss://eventsub.wss.twitch.tv/ws`
2. Receive `session_welcome` with `session.id`
3. Subscribe to `channel.chat.message` within 10 seconds (close code 4003 if not)
4. Receive `session_keepalive` if no events
5. Handle `session_reconnect` by connecting to new URL
6. Handle `revocation` if subscription is revoked

### Reconnect Flow
- Twitch sends `session_reconnect` 30 seconds before closing
- Use the provided `reconnect_url` as-is (do not modify)
- Old connection stays active until new one receives welcome
- Close old connection after receiving welcome on new
- Grace period: 30 seconds (close code 4004)

### Close Codes
| Code | Reason |
|------|--------|
| 4000 | Internal server error |
| 4001 | Client sent inbound traffic |
| 4002 | Client failed ping-pong |
| 4003 | Connection unused (no subscription within 10s) |
| 4004 | Reconnect grace time expired |
| 4005 | Network timeout |
| 4006 | Network error |
| 4007 | Invalid reconnect URL |

### Deduplication
- Messages may be delivered more than once
- Track `message_id` to prevent duplicate processing
- Deduplication cache expires after 10 minutes

## Event Numbers (1-10)

Viewers can activate events by typing a number in chat. No prefix needed.

| Number | Action | Cooldown |
|--------|--------|----------|
| `1` | zombie | 10s |
| `2` | spiders | 10s |
| `3` | slowness | 15s |
| `4` | blindness | 15s |
| `5` | creeper | 30s |
| `6` | storm | 60s |
| `7` | random_teleport | 20s |
| `8` | explosion | 30s |
| `9` | random_event | 45s |
| `10` | chickens | 0s |

### Behavior
- Numbers use the exact same pipeline as `!commands`
- Same cooldowns, same permissions, same Minecraft execution
- Only exact matches work: `1` yes, `hola 1` no, `!1` no
- Whitespace is trimmed: `"  1  "` = `"1"`
- Numbers outside 1-10 are ignored

### Configuration

The event number mapping is in `config.yaml`:

```yaml
events:
  "1": zombie
  "2": spiders
  "3": slowness
  "4": blindness
  "5": creeper
  "6": storm
  "7": random_teleport
  "8": explosion
  "9": random_event
  "10": chickens
```

The mapping can be customized by editing this section.

## Subscription: channel.chat.message

### Authorization

Requires a User Access Token with `user:read:chat` scope.

The token must be for the user specified in the condition's `user_id` parameter (or the broadcaster if `user_id` is omitted).

### Condition Parameters

```json
{
    "broadcaster_user_id": "1337",     // Required: channel to monitor
    "user_id": "9001"                  // Optional: filter to specific user
}
```

### Event Payload

```json
{
    "broadcaster_user_id": "1971641",
    "broadcaster_user_login": "streamer",
    "broadcaster_user_name": "streamer",
    "chatter_user_id": "4145994",
    "chatter_user_login": "viewer32",
    "chatter_user_name": "viewer32",
    "message_id": "cc106a89-1814-919d-454c-f4f2f970aae7",
    "message": {
        "text": "Hi chat",
        "fragments": [
            {
                "type": "text",
                "text": "Hi chat",
                "cheermote": null,
                "emote": null,
                "mention": null
            }
        ]
    },
    "color": "#00FF7F",
    "badges": [
        {"set_id": "subscriber", "id": "12", "info": "16"}
    ],
    "message_type": "text",
    "cheer": null,
    "reply": null,
    "channel_points_custom_reward_id": null
}
```

### Badges/Roles

The `badges` array contains role information:

| `set_id` | Meaning |
|-----------|---------|
| `broadcaster` | Channel owner |
| `moderator` | Moderator |
| `vip` | VIP user |
| `subscriber` | Subscriber |
| `artist` | Channel artist |
| `turbo` | Twitch Turbo |
| `premium` | Twitch Prime |

## Running

### Diagnostic Mode

Check Twitch configuration without connecting:

```bash
python main.py --check-twitch
```

Output:
```
ChatControl Twitch Diagnostic
========================================

[STEP] Configuration
----------------------------------------
[DIAG] Twitch: ENABLED
[DIAG] Channel: YourChannel
[DIAG] Broadcaster ID: 12345678
[DIAG] Client ID: set
[DIAG] Access Token: set
[DIAG] Configuration: VALID

[STEP] Token Validation
----------------------------------------
  [OK] Token valid
       Login: yourchannel
       User ID: 12345678
       Scopes: user:read:chat

[STEP] Scopes Check
----------------------------------------
  [OK] All required scopes present

[STEP] EventSub Readiness
----------------------------------------
  [OK] Broadcaster ID: 12345678
  [OK] WebSocket URL: wss://eventsub.wss.twitch.tv/ws

Ready for EventSub connection.
```

### With Twitch

```bash
python main.py
```

Requires valid Twitch credentials in `config.yaml`.

### Mock Mode (no Twitch, no Minecraft)

```bash
python main.py --mock
```

### Debug Logging

```bash
python main.py --mock -v
```

## Error Messages

### Configuration Errors

```
[ERROR] Twitch is enabled but client_id is missing.
[ERROR] Twitch is enabled but access_token is missing.
[ERROR] Twitch is enabled but broadcaster_id is missing.
[ERROR] Twitch is enabled but channel is missing.
```

### Authentication Errors

```
[ERROR] Twitch token validation failed: Invalid or expired token
[ERROR] Missing required scopes: user:read:chat
```

### EventSub Errors

```
[ERROR] Subscription failed: HTTP 403 - {"error":"Forbidden","message":"..."}
[WARNING] Subscription revoked: type=channel.chat.message status=authorization_revoked
```

## Troubleshooting

### Token Invalid or Expired

1. Run `python main.py --check-twitch`
2. If token is invalid, re-authorize with `user:read:chat` scope
3. Update `access_token` in `config.yaml`

### Missing Scopes

1. Check token has `user:read:chat` scope
2. Re-authorize if needed

### EventSub Subscription Fails

1. Verify `broadcaster_id` is correct (numeric)
2. Verify token belongs to the correct user
3. Check that `user:read:chat` scope is granted

### Connection Drops

The Bridge automatically reconnects with exponential backoff:
- Initial delay: 1 second
- Max delay: 30 seconds
- Max retries: 10

## Testing

```bash
python -m pytest tests/test_twitch.py tests/test_twitch_auth.py -v
```

## Limitations Without Real Twitch

- Cannot receive actual chat messages
- Cannot verify EventSub WebSocket connection
- Token validation requires network
- Subscription creation requires valid tokens
- `--check-twitch` will show token as invalid without real credentials
