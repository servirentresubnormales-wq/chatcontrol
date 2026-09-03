import pytest
from chat.command_parser import CommandParser, EVENT_NUMBER_MAP


class TestEventNumberMap:
    def test_map_has_all_numbers(self):
        for i in range(1, 11):
            assert str(i) in EVENT_NUMBER_MAP

    def test_map_values_are_valid_actions(self):
        valid_actions = {
            "zombie", "spiders", "slowness", "blindness", "creeper",
            "storm", "random_teleport", "explosion", "random_event", "chickens",
        }
        for action in EVENT_NUMBER_MAP.values():
            assert action in valid_actions

    def test_map_completeness(self):
        assert len(EVENT_NUMBER_MAP) == 10

    def test_1_is_zombie(self):
        assert EVENT_NUMBER_MAP["1"] == "zombie"

    def test_2_is_spiders(self):
        assert EVENT_NUMBER_MAP["2"] == "spiders"

    def test_3_is_slowness(self):
        assert EVENT_NUMBER_MAP["3"] == "slowness"

    def test_4_is_blindness(self):
        assert EVENT_NUMBER_MAP["4"] == "blindness"

    def test_5_is_creeper(self):
        assert EVENT_NUMBER_MAP["5"] == "creeper"

    def test_6_is_storm(self):
        assert EVENT_NUMBER_MAP["6"] == "storm"

    def test_7_is_random_teleport(self):
        assert EVENT_NUMBER_MAP["7"] == "random_teleport"

    def test_8_is_explosion(self):
        assert EVENT_NUMBER_MAP["8"] == "explosion"

    def test_9_is_random_event(self):
        assert EVENT_NUMBER_MAP["9"] == "random_event"

    def test_10_is_chickens(self):
        assert EVENT_NUMBER_MAP["10"] == "chickens"


class TestEventNumberParsing:
    def setup_method(self):
        self.parser = CommandParser(prefix="!")

    @pytest.mark.parametrize("number,expected_action", [
        ("1", "zombie"),
        ("2", "spiders"),
        ("3", "slowness"),
        ("4", "blindness"),
        ("5", "creeper"),
        ("6", "storm"),
        ("7", "random_teleport"),
        ("8", "explosion"),
        ("9", "random_event"),
        ("10", "chickens"),
    ])
    def test_valid_event_numbers(self, number, expected_action):
        result = self.parser.parse(number)
        assert result is not None
        assert result.valid
        assert result.command == number
        assert result.action == expected_action
        assert result.raw_args == ""
        assert result.params == {}

    def test_event_number_with_spaces(self):
        result = self.parser.parse("  1  ")
        assert result is not None
        assert result.valid
        assert result.action == "zombie"

    def test_event_number_10_with_spaces(self):
        result = self.parser.parse("   10   ")
        assert result is not None
        assert result.valid
        assert result.action == "chickens"

    def test_empty_string(self):
        result = self.parser.parse("")
        assert result is None

    def test_whitespace_only(self):
        result = self.parser.parse("   ")
        assert result is None

    def test_zero_not_valid(self):
        result = self.parser.parse("0")
        assert result is None

    def test_eleven_not_valid(self):
        result = self.parser.parse("11")
        assert result is None

    def test_negative_number(self):
        result = self.parser.parse("-1")
        assert result is None

    def test_large_number(self):
        result = self.parser.parse("100")
        assert result is None

    def test_float(self):
        result = self.parser.parse("1.0")
        assert result is None

    def test_leading_zero(self):
        result = self.parser.parse("01")
        assert result is None

    def test_decimal(self):
        result = self.parser.parse("1.5")
        assert result is None

    def test_text_with_number_prefix(self):
        result = self.parser.parse("hola 1")
        assert result is None

    def test_number_with_text_suffix(self):
        result = self.parser.parse("1 hola")
        assert result is None

    def test_event_text(self):
        result = self.parser.parse("evento 1")
        assert result is None

    def test_exclamation_number(self):
        result = self.parser.parse("!1")
        assert result is not None
        assert not result.valid

    def test_prefixed_number(self):
        result = self.parser.parse("!10")
        assert result is not None
        assert not result.valid


class TestEventNumbersPreserveExistingCommands:
    def setup_method(self):
        self.parser = CommandParser(prefix="!")

    def test_zombie_with_prefix(self):
        result = self.parser.parse("!zombie")
        assert result is not None
        assert result.valid
        assert result.action == "zombie"

    def test_pollos_with_prefix(self):
        result = self.parser.parse("!pollos")
        assert result is not None
        assert result.valid
        assert result.action == "chickens"

    def test_number_without_prefix_takes_priority(self):
        result = self.parser.parse("1")
        assert result is not None
        assert result.valid
        assert result.action == "zombie"

    def test_prefixed_number_does_not_trigger_event(self):
        result = self.parser.parse("!1")
        assert result is None or (result is not None and not result.valid)


class TestEventNumberCustomMap:
    def test_custom_event_number_map(self):
        custom_map = {"1": "storm", "2": "zombie"}
        parser = CommandParser(prefix="!", event_number_map=custom_map)
        result = parser.parse("1")
        assert result is not None
        assert result.valid
        assert result.action == "storm"

    def test_custom_map_does_not_affect_default(self):
        custom_map = {"1": "storm"}
        parser = CommandParser(prefix="!", event_number_map=custom_map)
        result = parser.parse("2")
        assert result is None

    def test_empty_custom_map(self):
        parser = CommandParser(prefix="!", event_number_map={})
        result = parser.parse("1")
        assert result is None


class TestEventNumberGetAvailableCommands:
    def test_includes_event_numbers(self):
        parser = CommandParser(prefix="!")
        commands = parser.get_available_commands()
        for i in range(1, 11):
            assert str(i) in commands

    def test_includes_prefix_commands(self):
        parser = CommandParser(prefix="!")
        commands = parser.get_available_commands()
        assert "zombie" in commands
        assert "pollos" in commands


class TestEventNumberGetActionForCommand:
    def test_number_returns_correct_action(self):
        parser = CommandParser(prefix="!")
        assert parser.get_action_for_command("1") == "zombie"
        assert parser.get_action_for_command("10") == "chickens"

    def test_prefix_command_still_works(self):
        parser = CommandParser(prefix="!")
        assert parser.get_action_for_command("zombie") == "zombie"
        assert parser.get_action_for_command("pollos") == "chickens"

    def test_invalid_command_returns_none(self):
        parser = CommandParser(prefix="!")
        assert parser.get_action_for_command("invalid") is None
