# ChatControl Actions

## Overview

Actions are immediate, one-shot operations that modify the Minecraft world.

## Chunk-Restricted Positioning

All position-based events are restricted to the player's current chunk. The system:

1. Gets the chunk where the streamer is located
2. Generates a random X/Z within that chunk's bounds (0-15 relative)
3. Finds a safe Y position (no lava, no solid blocks, has ground)
4. Validates minimum distance from streamer when possible
5. Never crosses into neighboring chunks

Configuration:
```yaml
spawn:
  min-distance: 2    # Minimum blocks from streamer
  max-attempts: 20   # Search attempts before fallback
```

If no valid position is found after max attempts, the action fails gracefully.

## Registered Actions

| Action | Dangerous | Cooldown | Bypasses |
|--------|-----------|----------|----------|
| `zombie` | Yes | 10s | - |
| `spiders` | Yes | 15s | - |
| `slowness` | No | 20s | - |
| `blindness` | No | 20s | - |
| `creeper` | Yes | 30s | - |
| `storm` | No | 60s | - |
| `random_teleport` | No | 60s | - |
| `explosion` | Yes | 30s | - |
| `random_event` | Yes | 60s | - |
| `chickens` | No | 0s | Cooldown + Rate Limit |
| `give_item` | No | 3s | - |
| `summon_mob` | Yes | 5s | - |
| `apply_effect` | No | 4s | - |

## Action Details

### zombie
Spawns a zombie in the player's current chunk.
- Position is always within the chunk boundaries
- Minimum distance from streamer when possible

### spiders
Spawns multiple spiders in the player's current chunk.
- `amount` (int, default: 4) - Number of spiders (max: 20)
- All spiders stay within the chunk boundaries

### slowness
Applies Slowness effect to the player.
- `duration` (int, default: 200) - Duration in ticks (max: 6000)
- `amplifier` (int, default: 1) - Effect level (0-10)

### blindness
Applies Blindness effect to the player.
- `duration` (int, default: 160) - Duration in ticks (max: 6000)
- `amplifier` (int, default: 0) - Effect level (0-10)

### creeper
Spawns a creeper in the player's current chunk.
- Position is always within the chunk boundaries

### storm
Starts a thunderstorm.
- `duration` (int, default: 600) - Duration in ticks
- `thunder` (boolean, default: true) - Enable thunder

### random_teleport
Teleports player to a random safe location within their current chunk.
- `max-attempts` (int, default: 20) - Search attempts within chunk
- Never teleports outside the current chunk
- Validates: safe ground, no lava, no void, has space

### explosion
Creates an explosion in the player's current chunk.
- `radius` (float, default: 3.0) - Explosion power (max: 10.0)
- `fire` (boolean, default: false) - Create fire
- `destroy-blocks` (boolean, default: false) - Destroy blocks
- Explosion position is within the chunk

### random_event
Executes a random action from the configured list.
- `actions` (array, optional) - List of allowed action names

### chickens
Spawns chickens in the player's current chunk. Bypasses cooldown and rate limit.
- `amount` (int, default: 1) - Number of chickens (max: 10)
- All chickens stay within the chunk boundaries

### give_item
Gives items to the player.
- `item` (string, default: "minecraft:stone") - Item ID
- `count` (int, default: 1) - Item count (max: 64)

### summon_mob
Summons any mob type near the player.
- `mob` (string, default: "minecraft:zombie") - Entity type ID
- `count` (int, default: 1) - Number of mobs (max: 10)

### apply_effect
Applies any potion effect to the player.
- `effect` (string, default: "minecraft:speed") - Effect ID
- `duration` (int, default: 200) - Duration in ticks (max: 6000)
- `amplifier` (int, default: 0) - Effect level (0-10)

## Blocked Items (give_item)
- command_block
- barrier
- bedrock
- end_portal
- structure_block

## Blocked Effects (apply_effect)
- instant_damage
- wither

## Permanently Blocked Actions
- stop_server
- op_player
- deop_player
- ban_player
- whitelist
