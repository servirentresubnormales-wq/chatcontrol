# ChatControl

Minecraft Fabric mod (1.21.1) that lets Twitch chat control the game during streams.

```
Twitch Chat → Python Bridge → TCP/JSON (port 8765) → Fabric Mod → Minecraft
```

## Components

| Component | Location | Language | Description |
|-----------|----------|----------|-------------|
| Core | `chatcontrol-mod/` | Java 21 | Fabric server mod, TCP/JSON receiver, action executor |
| Bridge | `bridge/` | Python 3.11+ | Twitch EventSub client, command parser, cooldown manager |
| Backend | `web/` | Python/Flask | API server, Twitch OAuth, database |
| Frontend | `site/` | Astro | Static site, landing page, dashboard |

## Quick Start

### Prerequisites

- Minecraft 1.21.1 server with Fabric Loader 0.16.14+
- Java 21 (JDK)
- Python 3.11+
- Node.js 20+ (for frontend)
- Twitch Developer Application

### Install Core

```bash
cd chatcontrol-mod
./gradlew build
# Copy build/libs/chatcontrol-1.0.0.jar to server's mods/ folder
```

### Install Bridge

```bash
cd bridge
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
cp config.example.yaml config.yaml
# Edit config.yaml with your settings
```

### Configure Twitch

```bash
python main.py --twitch-login    # OAuth flow
python main.py --check-twitch    # Verify config
python main.py --check-minecraft # Verify Core connection
```

### Start Bridge

```bash
python main.py
```

Viewers type numbers 1-10 in Twitch chat to trigger events.

### Run Frontend (Development)

```bash
cd site
npm install
npm run dev
# Open http://localhost:4321/chatcontrol/
```

## Available Events

| # | Action | Cooldown |
|---|--------|----------|
| 1 | Zombie spawn | 10s |
| 2 | Spider spawn | 10s |
| 3 | Slowness effect | 15s |
| 4 | Blindness effect | 15s |
| 5 | Creeper spawn | 30s |
| 6 | Thunderstorm | 60s |
| 7 | Random teleport | 20s |
| 8 | Explosion | 30s |
| 9 | Random event | 45s |
| 10 | Chicken rain | 0s |

## Web Dashboard

### Frontend (Static)

```bash
cd site
npm install
npm run dev          # Development
npm run build        # Production build
```

### Backend (Flask API)

```bash
cd web
pip install -r requirements.txt
cp .env.example .env
# Edit .env with Twitch credentials
python main.py
# Open http://localhost:5000
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

## Running Tests

```bash
# Bridge tests (447 tests)
cd bridge
python -m pytest -v

# Core tests (130 tests)
cd chatcontrol-mod
./gradlew test

# Backend tests (40 tests)
cd web
python -m pytest tests/ -v

# Frontend build
cd site
npm run build
```

## Project Structure

```
chatcontrol-mod/          Java Core (Fabric mod)
├── src/main/java/com/chatcontrol/
│   ├── ChatControlMod.java
│   ├── actions/           Action handlers (zombie, spiders, etc.)
│   ├── network/           TCP server, auth, protocol
│   ├── protection/        Safety checker
│   └── config/            ModConfig
bridge/                    Python Bridge
├── main.py                Entry point
├── core/                  Config, protocol, models
├── chat/                  Command parser, pipeline
├── minecraft/             TCP client
├── platforms/             Twitch integration
├── cooldowns/             Cooldown manager
├── mocks/                 CoreMock for testing
└── tests/                 447 tests
web/                       Flask Backend (API)
├── app.py                 Routes, API
├── models.py              SQLite models
├── twitch_oauth.py        OAuth handler
└── templates/             Login, dashboard
site/                      Astro Frontend (Static)
├── src/pages/             Pages (index, dashboard, login)
├── src/components/        UI components
├── src/layouts/           Page layouts
├── src/data/              Mock data
└── public/                Static assets
```

## GitHub Pages

Frontend is deployed to GitHub Pages via GitHub Actions.

```bash
https://servirentresubnormales-wq.github.io/chatcontrol/
```

See `docs/GITHUB_PAGES.md` for configuration details.

## Security

- Auth token required over TCP (constant-time comparison)
- `config.yaml` and `.env` excluded from git via `.gitignore`
- Never commit secrets or credentials
- Frontend contains no secrets (mock data only)

## License

MIT
