# ChatControl Bridge

Python client that connects to the Minecraft ChatControl Core via TCP/JSON, with optional Twitch integration.

## Requirements

- Python 3.11+
- A running Minecraft server with ChatControl mod installed (for live mode)
- Twitch Developer Application (for Twitch integration)

## Installation

```bash
cd bridge
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

## Configuration

Edit `config.yaml`:

```yaml
minecraft:
  host: "127.0.0.1"
  port: 8765
  auth_token: ""

bridge:
  target_player: "Streamer"
  reconnect_delay: 5
  request_timeout: 5

commands:
  prefix: "!"
  cooldowns:
    zombie: 10
    chickens: 0

twitch:
  enabled: false
  client_id: ""
  client_secret: ""
  access_token: ""
  broadcaster_id: ""
  bot_user_id: ""
  channel: ""
```

## Running

### Diagnostic Mode (check Twitch configuration)

```bash
python main.py --check-twitch
```

Validates Twitch configuration, token, scopes, and EventSub readiness without connecting.

### Mock mode (no Minecraft, no Twitch)

```bash
python main.py --mock
```

### Live mode (requires Minecraft server)

```bash
python main.py
```

### With Twitch integration

1. Configure `twitch:` section in `config.yaml`
2. Run: `python main.py`

### Options

```
-c, --config PATH   Path to config.yaml
--mock              Run in mock mode (no Minecraft/Twitch connection)
--check-twitch      Run Twitch diagnostics (no Minecraft connection)
-v, --verbose       Enable debug logging
```

## Architecture

```
Twitch → Integration → ChatMessage → Parser → Cooldown → Builder → Client → Core → Minecraft
Console Input  ──────────────────────────────────────────────────────────────→ Core → Minecraft
```

- **Command Parser**: Parses `!command` text into structured data
- **Command Builder**: Converts parsed commands into BridgeRequest objects
- **Minecraft Client**: Handles TCP connection, reconnection, serialization
- **Cooldown Manager**: Prevents spam (additional layer; Core has its own protection)
- **Twitch Integration**: EventSub WebSocket for live chat

## Available Commands

### Prefixed Commands

| Command | Action | Cooldown |
|---------|--------|----------|
| `!zombie` | zombie | 10s |
| `!spiders` | spiders | 10s |
| `!slowness` | slowness | 15s |
| `!blindness` | blindness | 15s |
| `!creeper` | creeper | 30s |
| `!storm` | storm | 60s |
| `!randomtp` | random_teleport | 20s |
| `!explosion` | explosion | 30s |
| `!random` | random_event | 45s |
| `!pollos` | chickens | 0s |
| `!give` | give_item | 20s |
| `!summon` | summon_mob | 10s |
| `!effect` | apply_effect | 15s |

### Event Numbers (1-10)

Viewers can also activate events by typing a number in chat (no prefix needed):

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

Examples:
- `1` = `!zombie`
- `10` = `!pollos`

Numbers use the same cooldowns, permissions, and pipeline as prefixed commands.

## Running Tests

```bash
python -m pytest -v
```

## Documentation

- `docs/TWITCH.md` — Twitch integration setup and EventSub details
- `README.md` — This file

## What This Does NOT Include Yet

- OBS overlay
- Super Chat / Membership handling
- Token refresh automation
- User economy / points
- Votations

These will be built on top of this base.
