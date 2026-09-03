import pytest
from chat.command_parser import CommandParser, ParsedCommand


class TestCommandParser:
    def setup_method(self):
        self.parser = CommandParser(prefix="!")

    def test_parse_zombie(self):
        result = self.parser.parse("!zombie")
        assert result is not None
        assert result.valid
        assert result.command == "zombie"
        assert result.action == "zombie"

    def test_parse_pollos(self):
        result = self.parser.parse("!pollos")
        assert result is not None
        assert result.valid
        assert result.action == "chickens"

    def test_parse_chickens(self):
        result = self.parser.parse("!chickens")
        assert result is not None
        assert result.valid
        assert result.action == "chickens"

    def test_parse_pollo(self):
        result = self.parser.parse("!pollo")
        assert result is not None
        assert result.valid
        assert result.action == "chickens"

    def test_parse_unknown_command(self):
        result = self.parser.parse("!invalid")
        assert result is not None
        assert not result.valid
        assert "Unknown command" in result.error

    def test_parse_no_prefix(self):
        result = self.parser.parse("zombie")
        assert result is None

    def test_parse_empty(self):
        result = self.parser.parse("")
        assert result is None

    def test_parse_whitespace(self):
        result = self.parser.parse("   ")
        assert result is None

    def test_parse_slowness_with_args(self):
        result = self.parser.parse("!slowness 200 1")
        assert result is not None
        assert result.valid
        assert result.params["duration"] == 200
        assert result.params["amplifier"] == 1

    def test_parse_blindness_with_duration(self):
        result = self.parser.parse("!blindness 160")
        assert result is not None
        assert result.valid
        assert result.params["duration"] == 160

    def test_parse_zombie_with_radius(self):
        result = self.parser.parse("!zombie 6")
        assert result is not None
        assert result.valid
        assert result.params["radius"] == 6.0

    def test_parse_spiders_amount_radius(self):
        result = self.parser.parse("!spiders 8 10")
        assert result is not None
        assert result.valid
        assert result.params["amount"] == 8
        assert result.params["radius"] == 10

    def test_parse_storm_duration_thunder(self):
        result = self.parser.parse("!storm 300 true")
        assert result is not None
        assert result.valid
        assert result.params["duration"] == 300
        assert result.params["thunder"] is True

    def test_parse_storm_no_thunder(self):
        result = self.parser.parse("!storm 300 false")
        assert result is not None
        assert result.valid
        assert result.params["thunder"] is False

    def test_parse_randomtp_radius(self):
        result = self.parser.parse("!randomtp 50")
        assert result is not None
        assert result.valid
        assert result.action == "random_teleport"
        assert result.params["radius"] == 50

    def test_parse_explosion_radius(self):
        result = self.parser.parse("!explosion 5.5")
        assert result is not None
        assert result.valid
        assert result.params["radius"] == 5.5

    def test_parse_command_with_spaces(self):
        result = self.parser.parse("!zombie  ")
        assert result is not None
        assert result.valid
        assert result.action == "zombie"

    def test_parse_custom_prefix(self):
        parser = CommandParser(prefix="$")
        result = parser.parse("$zombie")
        assert result is not None
        assert result.valid
        assert result.action == "zombie"

    def test_parse_prefix_not_at_start(self):
        result = self.parser.parse("test !zombie")
        assert result is None

    def test_get_available_commands(self):
        commands = self.parser.get_available_commands()
        assert "zombie" in commands
        assert "pollos" in commands
        assert "chickens" in commands

    def test_register_custom_command(self):
        self.parser.register_command("undead", "zombie")
        result = self.parser.parse("!undead")
        assert result is not None
        assert result.valid
        assert result.action == "zombie"

    def test_get_action_for_command(self):
        assert self.parser.get_action_for_command("zombie") == "zombie"
        assert self.parser.get_action_for_command("pollos") == "chickens"
        assert self.parser.get_action_for_command("invalid") is None

    def test_parse_case_insensitive(self):
        result = self.parser.parse("!ZOMBIE")
        assert result is not None
        assert result.valid
        assert result.action == "zombie"
