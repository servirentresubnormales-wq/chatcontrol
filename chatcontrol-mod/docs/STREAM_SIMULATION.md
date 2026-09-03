# ChatControl Stream Simulation

## What is it

A complete local simulation of a Twitch stream. It runs the full Bridge pipeline with a mock Twitch chat and a mock Core server, testing everything without Internet or Minecraft.

## Flow

```
TwitchMock (simulated chat)
    ↓
ChatMessage
    ↓
ChatPipeline (REAL)
    ↓
CommandParser (REAL)
    ↓
CooldownManager (REAL)
    ↓
CommandBuilder (REAL)
    ↓
MinecraftClient (REAL)
    ↓
TCP (REAL)
    ↓
Authentication (REAL)
    ↓
CoreMock (simulated server)
```

## Quick start

### Run with a scenario file

```bash
cd bridge
python main.py --simulate-stream --scenario scenarios/basic_stream.yaml
```

### Run interactively

```bash
cd bridge
python main.py --simulate-stream
```

Then type messages like:

```
chat> ViewerA: 1
chat> ViewerB: 5
chat> ViewerC: 10
chat> quit
```

## Scenario format (YAML)

```yaml
name: my_test
messages:
  - user: ViewerA
    text: "1"

  - user: ViewerB
    text: "5"

  - user: ViewerC
    text: "10"
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | No | Scenario name |
| `messages` | Yes | List of messages |
| `messages[].user` | Yes | Display name |
| `messages[].text` | Yes | Chat message text |
| `messages[].message_id` | No | Custom ID (for dedup testing) |
| `messages[].delay` | No | Delay before this message (seconds) |

## Output format

Each message produces logs like:

```
[TWITCH] ViewerA: 1
[PARSE] action=zombie
[COOLDOWN] allowed
[BRIDGE] sending zombie to Core
[CORE] zombie -> SUCCESS
```

For cooldown-blocked messages:

```
[TWITCH] ViewerA: 1
[PARSE] action=zombie
[COOLDOWN] BLOCKED (9.5s remaining)
```

For ignored messages:

```
[TWITCH] ViewerX: hola
[PARSE] ignored (not a command)
```

## Summary report

At the end:

```
--------------------------------------------------
  SIMULATION SUMMARY
--------------------------------------------------
  Messages processed:      21
  Commands detected:       18
  Commands ignored:        3
  Actions sent:            17
  Cooldown blocked:        1
  Core errors:             0
  Auth failures:           0
--------------------------------------------------
  Simulation:              PASSED
==================================================
```

## What is real vs mock

| Component | Real/Mock |
|-----------|-----------|
| ChatPipeline | **REAL** |
| CommandParser | **REAL** |
| CooldownManager | **REAL** |
| CommandBuilder | **REAL** |
| MinecraftClient | **REAL** |
| TCP connection | **REAL** |
| Authentication | **REAL** |
| TwitchMock | Mock |
| CoreMock | Mock |

## Running tests

### Unit + integration tests

```bash
cd bridge
python -m pytest tests/test_stream_simulation.py -v
```

### All tests

```bash
cd bridge
python -m pytest -v
```

## Example scenario

See `scenarios/basic_stream.yaml` for a complete example that tests:
- All 10 event numbers
- Cooldown blocking
- Chickens rapid fire (no cooldown)
- Normal text (ignored)
- Invalid commands
- Prefix commands (!zombie)
- Multi-user same action

## Limitations

1. **No Minecraft** — CoreMock returns mock responses
2. **No real Twitch** — TwitchMock generates local messages
3. **No persistence** — Actions are not queued across restarts
4. **No EventSub** — No Twitch WebSocket connection
5. **Single connection** — One Bridge → Core connection

## Architecture

```
bridge/
├── mocks/
│   ├── core_mock.py           # CoreMock TCP server
│   └── twitch_mock.py         # TwitchMock message generator
├── scenarios/
│   └── basic_stream.yaml      # Example scenario
├── tests/
│   └── test_stream_simulation.py  # 39 tests
└── docs/
    └── STREAM_SIMULATION.md   # This file
```
