# ChatControl Repository

## Repository Information

- **Name**: `chatcontrol`
- **Visibility**: Private
- **Default Branch**: `main`
- **License**: MIT

## Repository Structure

```
chatcontrol/
├── README.md                 Root documentation
├── .gitignore                Git ignore rules
├── docs/                     Project documentation
│   └── REPOSITORY.md         This file
├── chatcontrol-mod/          Java Core (Fabric mod)
│   ├── src/                  Java source
│   ├── build.gradle          Build configuration
│   └── gradlew               Gradle wrapper
├── bridge/                   Python Bridge
│   ├── main.py               Entry point
│   ├── core/                 Protocol, config
│   ├── chat/                 Command parsing
│   ├── minecraft/            TCP client
│   ├── platforms/            Twitch integration
│   ├── cooldowns/            Cooldown manager
│   ├── mocks/                Testing utilities
│   └── tests/                447 tests
└── web/                      Flask Dashboard
    ├── app.py                Routes, API
    ├── models.py             SQLite models
    ├── templates/            HTML templates
    └── tests/                40 tests
```

## Setup Instructions

### Clone Repository

```bash
git clone git@github.com:YOUR_USERNAME/chatcontrol.git
cd chatcontrol
```

### Install Dependencies

#### Java Core

```bash
cd chatcontrol-mod
./gradlew build
```

Requires: Java 21 (JDK), Internet connection

#### Python Bridge

```bash
cd bridge
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
```

Requires: Python 3.11+

#### Web Dashboard

```bash
cd web
pip install -r requirements.txt
```

Requires: Python 3.11+

### Configuration

1. Copy `bridge/config.example.yaml` to `bridge/config.yaml`
2. Copy `web/.env.example` to `web/.env`
3. Edit configs with your settings (see DEPLOYMENT.md)

## Testing

### Bridge Tests

```bash
cd bridge
python -m pytest -v
# Expected: 447 tests passed
```

### Core Tests

```bash
cd chatcontrol-mod
./gradlew test
# Expected: 130 tests passed
```

### Web Tests

```bash
cd web
python -m pytest tests/ -v
# Expected: 40 tests passed
```

## Development Workflow

1. Create feature branch from `main`
2. Make changes
3. Run all tests to verify
4. Create pull request
5. Review and merge

## Security Notes

- Never commit `config.yaml`, `.env`, or any files containing secrets
- `.gitignore` is configured to exclude sensitive files
- Auth tokens use constant-time comparison
- All secrets are placeholder values in example configs

## CI/CD

Not configured yet. Consider adding:

- GitHub Actions for test automation
- Gradle build verification
- Python test suite
- Linting (checkstyle, flake8)

## Contributing

1. Fork the repository
2. Create feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Update documentation
6. Submit pull request

## Support

- Check `docs/DEPLOYMENT.md` for setup instructions
- Check `docs/ARCHITECTURE.md` for system design
- Check `docs/PROTOCOL.md` for TCP/JSON protocol details
