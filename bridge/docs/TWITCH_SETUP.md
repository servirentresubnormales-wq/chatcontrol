# Twitch Setup Guide — ChatControl

Step-by-step guide to connect ChatControl to your Twitch channel.

## Prerequisites

- Python 3.11+ installed
- Twitch account (the streamer account)
- Minecraft 1.21.1 with Fabric mod loader
- ChatControl Core mod installed

## Step 1: Create Twitch Application

1. Go to https://dev.twitch.tv/console
2. Log in with your Twitch account
3. Click **Register Your Application**
4. Fill in:
   - **Name**: `ChatControl`
   - **OAuth Redirect URL**: `http://localhost:3000`
   - **Category**: `Chat Bot`
5. Click **Create**
6. Note your **Client ID** and **Client Secret**

## Step 2: Configure config.yaml

Edit `config.yaml` and set:

```yaml
twitch:
  enabled: true
  client_id: "YOUR_CLIENT_ID"
  client_secret: "YOUR_CLIENT_SECRET"
  access_token: ""
  refresh_token: ""
  broadcaster_id: ""
  channel: "YOUR_TWITCH_USERNAME"
```

## Step 3: Authorize Your Account

Run the OAuth login command:

```bash
python main.py --twitch-login
```

This will:
1. Open your browser to Twitch authorization page
2. Ask you to log in and authorize the application
3. Redirect back to localhost:3000 with the authorization code
4. Exchange the code for access token + refresh token
5. Save tokens to `config.yaml`
6. Validate the token and show your user info

### What happens during authorization:

1. **URL Opens**: `https://id.twitch.tv/oauth2/authorize?...`
2. **You Log In**: Use your Twitch account (the streamer account)
3. **You Authorize**: Click "Authorize" to grant `user:read:chat` scope
4. **Callback**: Twitch redirects to `http://localhost:3000/?code=...&state=...`
5. **Tokens Saved**: `config.yaml` is updated with tokens

### Scopes Requested

- `user:read:chat` — Required to receive chat messages via EventSub

**Note**: This is the ONLY scope needed. No bot account required for reading your own chat.

## Step 4: Verify Configuration

Run the diagnostic command:

```bash
python main.py --check-twitch
```

Expected output:

```
ChatControl Twitch Diagnostic
========================================

[STEP] Configuration
----------------------------------------
[DIAG] Twitch: ENABLED
[DIAG] Channel: YourChannel
[DIAG] Broadcaster ID: 123456789
[DIAG] Client ID: set
[DIAG] Access Token: set
[DIAG] Configuration: VALID

[STEP] Token Validation
----------------------------------------
  [OK] Token valid
       Login: yourchannel
       User ID: 123456789
       Scopes: user:read:chat

[STEP] Scopes Check
----------------------------------------
  [OK] All required scopes present

[STEP] EventSub Readiness
----------------------------------------
  [OK] Broadcaster ID: 123456789
  [OK] WebSocket URL: wss://eventsub.wss.twitch.tv/ws

Ready for EventSub connection.
```

## Step 5: Start Minecraft

1. Start Minecraft 1.21.1 with Fabric
2. Create or load a world
3. Make sure the ChatControl mod is loaded (check logs for "ChatControl mod initialized")

## Step 6: Start the Bridge

```bash
python main.py
```

Expected output:

```
ChatControl Bridge starting...
Target: Streamer
Twitch integration: ENABLED (channel=YourChannel)
[INFO] Twitch token validated (login=yourchannel, user_id=123456789)
[INFO] Twitch EventSub client started
[INFO] EventSub session established (id=...)
[INFO] Subscribed to channel.chat.message (sub_id=...)
[INFO] Twitch integration ready — listening for chat messages
```

## Step 7: Test It

1. Open your Twitch channel in another browser/device
2. Type `1` in your own chat
3. Check the Bridge console — you should see:
   ```
   [INFO] Chat message from YourChannel: 1
   [OK] Action completed: zombie
   ```
4. Check Minecraft — a zombie should spawn in your chunk

## Troubleshooting

### "Token validation failed"
- Run `python main.py --twitch-login` again
- Make sure you're authorizing with the correct Twitch account

### "Missing required scopes"
- The token doesn't have `user:read:chat` scope
- Run `python main.py --twitch-login` to re-authorize

### "Subscription failed"
- Check that `broadcaster_id` is set correctly
- Run `python main.py --check-twitch` to verify

### "Minecraft Core unavailable"
- Make sure Minecraft is running with the ChatControl mod
- The mod listens on port 8765 by default

## Architecture

```
Twitch Chat
    ↓
EventSub WebSocket (wss://eventsub.wss.twitch.tv/ws)
    ↓
TwitchWSClient
    ↓
TwitchEventHandler (deduplication)
    ↓
ChatMessage
    ↓
ChatPipeline
    ↓
CommandParser (1-10 → action)
    ↓
CooldownManager (per-user)
    ↓
BridgeRequest
    ↓
MinecraftClient (TCP/JSON)
    ↓
ChatControl Core (Fabric)
    ↓
Minecraft World
```

## Security Notes

- **Never commit `config.yaml`** with real tokens
- **Tokens are stored locally only**
- **No secrets are logged** — only token prefix shown in diagnostics
- **Refresh tokens** are used to renew access tokens automatically

## Twitch Test Mode

Before running the full system with Minecraft, you can test the Twitch integration independently:

```bash
python main.py --twitch-test
```

### What it does

- Connects to **real Twitch** EventSub WebSocket
- Receives **real chat messages** from your channel
- Processes messages through the full pipeline (parser, cooldowns)
- Shows what action **would have been executed**
- Does **NOT** connect to Minecraft or execute any actions

### Expected output

When someone writes `1` in your chat:

```
[TWITCH] Viewer123 (ID: 123456): 1
[EVENT] Action: zombie
[TARGET] Streamer
[MODE] TEST — Minecraft action NOT executed
```

### How to use

1. Configure Twitch (Steps 1-4 above)
2. Run: `python main.py --twitch-test`
3. Open your Twitch channel in another browser
4. Type numbers `1-10` or commands like `!zombie`
5. Watch the console output
6. Press `CTRL+C` to stop

### What you can test

- ✅ Real Twitch connection
- ✅ EventSub subscription
- ✅ Message reception
- ✅ Event number parsing (1-10)
- ✅ Command parsing (!zombie, !spiders, etc.)
- ✅ Cooldown behavior
- ✅ Deduplication
- ✅ User info (name, ID, badges)
- ✅ Clean shutdown

### What you cannot test

- ❌ Minecraft actions (no server)
- ❌ Entity spawning
- ❌ World modifications
