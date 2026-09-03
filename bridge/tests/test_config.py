import pytest
import tempfile
import os
import yaml
from pathlib import Path
from core.config import Config, load_config, _deep_merge, DEFAULT_CONFIG


class TestDeepMerge:
    def test_simple_merge(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        base = {"a": {"x": 1, "y": 2}}
        override = {"a": {"y": 3, "z": 4}}
        result = _deep_merge(base, override)
        assert result == {"a": {"x": 1, "y": 3, "z": 4}}

    def test_override_replaces_non_dict(self):
        base = {"a": {"x": 1}}
        override = {"a": "string"}
        result = _deep_merge(base, override)
        assert result["a"] == "string"


class TestConfig:
    def test_default_config(self):
        config = Config(DEFAULT_CONFIG)
        assert config.host == "127.0.0.1"
        assert config.port == 8765
        assert config.auth_token == ""
        assert config.target_player == "Streamer"
        assert config.reconnect_delay == 5
        assert config.request_timeout == 5
        assert config.command_prefix == "!"

    def test_get_cooldown(self):
        config = Config(DEFAULT_CONFIG)
        assert config.get_cooldown("zombie") == 10
        assert config.get_cooldown("chickens") == 0
        assert config.get_cooldown("unknown") == 0

    def test_get_all_cooldowns(self):
        config = Config(DEFAULT_CONFIG)
        cooldowns = config.get_all_cooldowns()
        assert "zombie" in cooldowns
        assert "chickens" in cooldowns
        assert cooldowns["zombie"] == 10


class TestLoadConfig:
    def test_load_existing_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"minecraft": {"host": "192.168.1.1", "port": 9999}}, f)
            f.flush()
            path = f.name

        try:
            config = load_config(path)
            assert config.host == "192.168.1.1"
            assert config.port == 9999
            assert config.target_player == "Streamer"
        finally:
            os.unlink(path)

    def test_load_missing_file_uses_defaults(self):
        config = load_config("nonexistent.yaml")
        assert config.host == "127.0.0.1"
        assert config.port == 8765

    def test_load_partial_config(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"bridge": {"target_player": "Gamer"}}, f)
            f.flush()
            path = f.name

        try:
            config = load_config(path)
            assert config.target_player == "Gamer"
            assert config.host == "127.0.0.1"
        finally:
            os.unlink(path)

    def test_load_empty_config(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({}, f)
            f.flush()
            path = f.name

        try:
            config = load_config(path)
            assert config.host == "127.0.0.1"
        finally:
            os.unlink(path)

    def test_load_custom_cooldowns(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({
                "commands": {
                    "cooldowns": {
                        "zombie": 20,
                        "custom_action": 5,
                    }
                }
            }, f)
            f.flush()
            path = f.name

        try:
            config = load_config(path)
            assert config.get_cooldown("zombie") == 20
            assert config.get_cooldown("custom_action") == 5
            assert config.get_cooldown("chickens") == 0
        finally:
            os.unlink(path)
