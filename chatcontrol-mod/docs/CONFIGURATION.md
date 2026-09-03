# ChatControl Configuration

Config file location: `config/chatcontrol.json`

## Global Settings

```json
{
  "enabled": false,
  "autoStart": false,
  "networkEnabled": true,
  "networkPort": 8765,
  "loggingEnabled": true,
  "maxActionsPerMinute": 30,
  "defaultCooldownSeconds": 5,
  "globalCooldownSeconds": 1,
  "allowDangerousActions": false,
  "maxItemsPerAction": 64,
  "maxMobsPerAction": 10
}
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | boolean | false | System active state |
| `autoStart` | boolean | false | Auto-enable on server start |
| `networkEnabled` | boolean | true | Enable TCP server |
| `networkPort` | int | 8765 | TCP listening port |
| `loggingEnabled` | boolean | true | Enable detailed logging |
| `maxActionsPerMinute` | int | 30 | Rate limit per minute |
| `defaultCooldownSeconds` | int | 5 | Default cooldown for actions |
| `globalCooldownSeconds` | int | 1 | Cooldown between ANY actions |
| `allowDangerousActions` | boolean | false | Allow dangerous actions |
| `maxItemsPerAction` | int | 64 | Max items per give_item |
| `maxMobsPerAction` | int | 10 | Max mobs per summon_mob |

## Per-Action Settings

```json
{
  "actionConfigs": {
    "zombie": {
      "enabled": true,
      "cooldown": 10,
      "radius": 4
    },
    "spiders": {
      "enabled": true,
      "cooldown": 15,
      "amount": 4,
      "radius": 5
    }
  }
}
```

### Action Config Fields

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | boolean | Whether action is available |
| `cooldown` | int | Cooldown in seconds |
| `radius` | int/float | Spawn/explosion radius |
| `amount` | int | Entity count |
| `duration` | int | Effect/weather duration in ticks |
| `amplifier` | int | Effect level |
| `thunder` | boolean | Enable thunder |
| `fire` | boolean | Create fire |
| `destroy-blocks` | boolean | Destroy blocks |
| `max-attempts` | int | Search attempts |
| `actions` | array | Allowed actions for random_event |

## Default Action Configs

| Action | Cooldown | Key Settings |
|--------|----------|--------------|
| zombie | 10s | radius: 4 |
| spiders | 15s | amount: 4, radius: 5 |
| slowness | 20s | duration: 200, amplifier: 1 |
| blindness | 20s | duration: 160, amplifier: 0 |
| creeper | 30s | radius: 4 |
| storm | 60s | duration: 600, thunder: true |
| random_teleport | 60s | radius: 30, max-attempts: 20 |
| explosion | 30s | radius: 3.0, fire: false, destroy-blocks: false |
| random_event | 60s | - |
| chickens | 0s | amount: 1, radius: 4 |

## Hot Reload

Use `/chatcontrol reload` in-game to reload configuration without restarting.
Requires permission level 2.
