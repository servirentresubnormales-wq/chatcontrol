# ChatControl Deployment Guide

## Overview

ChatControl consists of two components:

1. **ChatControl Core** — Fabric mod running on Minecraft server
2. **ChatControl Bridge** — Python process connecting Twitch to Core

## Prerequisites

### Minecraft Server

- Minecraft 1.21.1
- Java 21
- Fabric Loader 0.16.14+
- Fabric API 0.116.17+1.21.1

### Bridge

- Python 3.11+
- pip
- Twitch account with EventSub access

## Step 1: Install Core

1. Install Minecraft server with Fabric
2. Download `chatcontrol-1.0.0.jar`
3. Place in `mods/` directory
4. Start server once to generate `config/chatcontrol.json`
5. Edit `config/chatcontrol.json`:

```json
{
  "enabled": true,
  "autoStart": true,
  "networkEnabled": true,
  "networkPort": 8765,
  "authentication": {
    "enabled": true,
    "token": "YOUR_SECRET_TOKEN_HERE"
  }
}
```

6. Restart server
7. Verify in logs: `[ChatControl] Network receiver listening on port 8765`

## Step 2: Install Bridge

```bash
cd bridge
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
```

## Step 3: Configure Bridge

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml`:

```yaml
minecraft:
  host: "YOUR_SERVER_IP"
  port: 8765
  auth_token: "YOUR_SECRET_TOKEN_HERE"

bridge:
  target_player: "YOUR_MINECRAFT_USERNAME"
```

## Step 4: Configure Twitch

### Option A: OAuth Login (Recommended)

```bash
python main.py --twitch-login
```

Follow the browser prompt to authorize.

### Option B: Manual

1. Create Twitch application at https://dev.twitch.tv/console/apps
2. Set `client_id` and `client_secret` in `config.yaml`
3. Generate access token with `user:read:chat` scope
4. Set `access_token` and `channel` in `config.yaml`

## Step 5: Verify

### Check Twitch

```bash
python main.py --check-twitch
```

Expected: `[OK] Token valid`, `[OK] All required scopes present`

### Check Minecraft Core

```bash
python main.py --check-minecraft
```

Expected: `Minecraft Core is READY`

## Step 6: Start

```bash
python main.py
```

## Diagnostic Commands

| Command | Description |
|---------|-------------|
| `python main.py --check-twitch` | Verify Twitch configuration |
| `python main.py --check-minecraft` | Verify Core connection |
| `python main.py --twitch-login` | OAuth flow for Twitch |
| `python main.py --twitch-test` | Test Twitch without Minecraft |
| `python main.py --simulate-stream` | Full local simulation |
| `python main.py --mock` | Interactive mode without Minecraft |

## Troubleshooting

### Core not reachable

```
[FAIL] Connection refused
```

- Check Minecraft server is running
- Check `networkPort` in `chatcontrol.json`
- Check firewall allows port 8765

### Authentication failed

```
[FAIL] Authentication failed: Invalid token
```

- Verify token matches in both configs
- Check for typos or extra spaces

### Twitch not connecting

```
[FAIL] Token validation failed
```

- Run `python main.py --twitch-login` to refresh token
- Check `client_id` and `client_secret`

### No players online

```
[ERROR] NO_PLAYERS_ONLINE
```

- Ensure a player is connected to Minecraft
- The target player must be online

## Architecture

```
Twitch Chat
    |
    v
[ChatControl Bridge] (Python)
    |
    v  TCP/JSON on port 8765
    |
[ChatControl Core] (Fabric Mod)
    |
    v
Minecraft World
```

## Security Notes

- Never commit `config.yaml` to git
- Use a strong, unique auth token
- The auth token is sent in plaintext (TCP)
- For production, consider running on a trusted network
- Rotate tokens if compromised

## First Test

1. Start Minecraft server with Core mod
2. Connect to Minecraft as the streamer
3. Start Bridge: `python main.py`
4. Open Twitch chat
5. Type: `1`
6. Verify zombie spawns near you in-game
