# ChatControl - Minecraft Mod Core

Minecraft server-side mod that allows Twitch/YouTube chat to control the game.

## Requirements

- **Java 21** (JDK, not JRE)
- **Gradle 9.x** (will be downloaded automatically by wrapper)
- **Internet connection** (to download dependencies)

## Quick Setup (Recommended)

The easiest way to set up this project:

1. Go to https://fabricmc.net/develop/template/
2. Fill in:
   - Minecraft version: `1.21.1`
   - Mod name: `ChatControl`
   - Mod ID: `chatcontrol`
   - Package name: `com.chatcontrol`
   - Loader: Fabric
3. Download the generated template
4. Copy `gradle/wrapper/gradle-wrapper.jar` from the template to this project
5. Copy the `gradlew` and `gradlew.bat` from the template to this project

## Manual Setup

If you have Gradle installed:

```bash
cd chatcontrol-mod
gradle wrapper
```

## Build

```bash
./gradlew build
```

The compiled mod JAR will be at:
`build/libs/chatcontrol-1.0.0.jar`

## Install

1. Install Fabric server for Minecraft 1.21.1
2. Copy `chatcontrol-1.0.0.jar` to the server's `mods/` folder
3. Start the server

## Test Commands

In-game (OP required):

```
/chatcontrol start    - Activate the system
/chatcontrol stop     - Deactivate the system
/chatcontrol status   - Show system status
/chatcontrol reload   - Reload configuration
/chatcontrol reset    - Reset all state
```

## Network Protocol

The mod listens on port 8765 (configurable) for TCP connections.

Send JSON commands:

```json
{"action": "give_item", "player": "PlayerName", "params": {"item": "minecraft:diamond", "count": "5"}}
{"action": "summon_mob", "player": "PlayerName", "params": {"mob": "minecraft:zombie", "count": "3"}}
{"action": "apply_effect", "player": "PlayerName", "params": {"effect": "minecraft:speed", "duration": "400", "amplifier": "1"}}
```

Response:
```json
{"success": true, "message": "Action 'give_item' executed."}
```

## Configuration

Config file: `config/chatcontrol.json`

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

## Project Structure

```
chatcontrol-mod/
├── src/main/java/com/chatcontrol/
│   ├── ChatControlMod.java          # Entry point
│   ├── config/ModConfig.java        # Configuration
│   ├── state/SystemState.java       # Global state
│   ├── commands/                    # Game commands
│   ├── actions/                     # Action system
│   ├── events/                      # Event system
│   ├── protection/SafetyChecker.java # Security
│   └── network/CommandReceiver.java  # TCP server
├── src/main/resources/
│   ├── fabric.mod.json
│   └── chatcontrol.mixins.json
├── build.gradle
├── gradle.properties
└── settings.gradle
```

## Phase 1 Features

- [x] Mod entry point
- [x] Configuration system (JSON)
- [x] Commands: start, stop, status, reload, reset
- [x] Action system with registry
- [x] Give item action
- [x] Summon mob action
- [x] Apply effect action
- [x] TCP network receiver
- [x] Safety checker (blocked actions, rate limits)
- [x] Cooldown system
- [ ] Twitch integration (Phase 2)
- [ ] YouTube integration (Phase 2)
- [ ] Voting system (Phase 3)
- [ ] Event system (Phase 3)

## License

MIT
