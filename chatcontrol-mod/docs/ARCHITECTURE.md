# ChatControl Architecture

## Overview

ChatControl is a Minecraft Fabric mod (1.21.1, Java 21) that allows Twitch/YouTube chat to control a Minecraft game during streams.

```
Twitch/YouTube Chat
       |
       v
   [Bridge] (Python, Phase 2)
       |
       v  TCP/JSON on port 8765
       |
   [ChatControl Mod] (Fabric Server-Side)
       |
       +-- CommandReceiver (TCP Server)
       |       |
       |       v
       |   ActionExecutor
       |       |
       |       +-- Cooldowns
       |       +-- Rate Limiting
       |       +-- Global Cooldown
       |       +-- Safety Checks
       |       |
       |       v
       |   ActionHandler implementations
       |       |
       |       v
       |   Minecraft World
       |
       +-- EventRegistry (Future: complex timed events)
       |
       +-- ChatControlCommands (/chatcontrol start|stop|status|reload|reset)
```

## Core Components

### ActionHandler Interface
Every action implements this interface:
- `getName()` - unique action identifier
- `getDescription()` - human-readable description
- `getDefaultCooldownSeconds()` - per-action cooldown
- `isDangerous()` - requires `allowDangerousActions` config
- `bypassCooldown()` - skips cooldown check
- `bypassRateLimit()` - skips rate limit check
- `execute(server, target, params)` - performs the action

### ActionRegistry
Maps action names to ActionHandler instances. Supports:
- Registration
- Lookup by name
- Listing registered actions

### ActionExecutor
Central router that:
1. Checks system is enabled
2. Validates action is not blocked
3. Checks dangerous action permission
4. Applies per-action cooldown
5. Applies global cooldown
6. Applies rate limiting
7. Validates parameters via SafetyChecker
8. Executes the action
9. Updates cooldowns and counters

### SpawnUtils & ChunkPositionHelper
Handles chunk-restricted positioning for all spawn/teleport/explosion actions:

```
Streamer
   ↓
Current Chunk (getChunkPos)
   ↓
Random X/Z within chunk (0-15 block range)
   ↓
Safe Y (check air, ground, no lava)
   ↓
Validate (min distance, max attempts)
   ↓
Execute Action
```

Key classes:
- `ChunkPositionHelper` - Pure logic, fully testable without Minecraft
- `SpawnUtils` - Minecraft API wrapper using ChunkPositionHelper
- `SpawnConfig` - Configuration (min-distance, max-attempts)

Rules:
- Never crosses chunk boundaries
- Minimum distance from streamer when possible
- Safe Y means: air at position, air above, solid below, no lava
- Fallback to any safe position if min-distance impossible
- Fails gracefully after max attempts

### SafetyChecker
- Blocks dangerous actions (stop_server, op_player, etc.)
- Validates parameters per action (amounts, radii, durations)
- Blocks dangerous items and effects

### CommandReceiver
TCP server that:
- Accepts JSON commands on configurable port
- Parses BridgeRequest protocol
- **Authenticates connections** (when enabled in config)
- Schedules execution on server thread via `server.execute()`
- Returns BridgeResponse with error codes

### AuthenticationManager
Per-connection authentication state machine:
- Validates tokens using constant-time comparison
- Tracks connection states: IDLE → AUTHENTICATING → AUTHENTICATED/REJECTED
- Rate limits failed auth attempts
- Enforces auth timeout

Flow:
```
Bridge connects
    ↓
[Auth enabled?]
    ├─ No → AUTHENTICATED (skip handshake)
    └─ Yes → Send auth request
              ↓
         [Validate token]
              ├─ Success → AUTHENTICATED → accept commands
              └─ Failure → REJECTED → close connection
```

### EventRegistry
For complex, timed, chained events (Phase 2+):
- Weather events
- Boss spawns
- Votations
- Events with duration

### SystemState
Thread-safe global state:
- enabled/disabled
- total actions executed
- uptime tracking

## Threading Model

- **Server Thread**: All Minecraft operations (entity spawning, world modification, player interaction)
- **Network Threads**: TCP connection handling, JSON parsing
- **Bridge**: External Python process connecting via TCP

The CommandReceiver uses `CompletableFuture` + `server.execute()` to bridge network threads to the server thread.

## Configuration

Config file: `config/chatcontrol.json`

Contains:
- Network settings (port, enabled)
- Global limits (max actions/min, cooldowns)
- Per-action settings (enabled, cooldown, parameters)
- Safety settings (allow dangerous actions, max items/mobs)

## Extension Points

### Adding a New Action
1. Create class implementing `ActionHandler`
2. Register in `ChatControlMod.registerActions()`
3. Add default config in `ModConfig.createActionDefaults()`
4. Add validation in `SafetyChecker.validateParams()`

### Adding a New Event
1. Create class implementing `EventDefinition`
2. Register in `EventRegistry`
3. Events can trigger multiple actions over time
