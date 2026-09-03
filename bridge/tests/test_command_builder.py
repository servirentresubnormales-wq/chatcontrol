from minecraft.command_builder import build_action, build_action_with_defaults, ACTION_PARAM_DEFAULTS
from core.models import BridgeRequest


class TestBuildAction:
    def test_basic_action(self):
        req = build_action(action="zombie", target="Player1")
        assert req.action == "zombie"
        assert req.target == "Player1"
        assert req.source == "bridge"
        assert req.protocol_version == 1

    def test_action_with_source(self):
        req = build_action(action="zombie", target="Player1", source="twitch", user="Viewer")
        assert req.source == "twitch"
        assert req.user == "Viewer"

    def test_action_with_params(self):
        req = build_action(action="zombie", target="Player1", params={"radius": 6})
        assert req.params == {"radius": 6}

    def test_action_with_custom_message_id(self):
        req = build_action(action="zombie", message_id="custom_id")
        assert req.message_id == "custom_id"

    def test_action_generates_message_id(self):
        req = build_action(action="zombie")
        assert req.message_id is not None
        assert len(req.message_id) == 32

    def test_action_with_metadata(self):
        req = build_action(action="zombie", metadata={"key": "value"})
        assert req.metadata == {"key": "value"}

    def test_action_with_auth_token(self):
        req = build_action(action="zombie", auth_token="token123")
        assert req.auth_token == "token123"

    def test_action_no_params(self):
        req = build_action(action="zombie")
        assert req.params is None or req.params == {}


class TestBuildActionWithDefaults:
    def test_zombie_defaults(self):
        req = build_action_with_defaults(action="zombie", target="Player1")
        assert req.params == {"radius": 4}

    def test_spiders_defaults(self):
        req = build_action_with_defaults(action="spiders", target="Player1")
        assert req.params == {"amount": 4, "radius": 5}

    def test_chickens_defaults(self):
        req = build_action_with_defaults(action="chickens", target="Player1")
        assert req.params == {"amount": 1, "radius": 4}

    def test_storm_defaults(self):
        req = build_action_with_defaults(action="storm", target="Player1")
        assert req.params == {"duration": 600, "thunder": True}

    def test_override_defaults(self):
        req = build_action_with_defaults(action="zombie", target="Player1", overrides={"radius": 10})
        assert req.params == {"radius": 10}

    def test_unknown_action_no_params(self):
        req = build_action_with_defaults(action="unknown_action", target="Player1")
        assert req.params is None or req.params == {}

    def test_kwargs_override(self):
        req = build_action_with_defaults(action="zombie", target="Player1", radius=8)
        assert req.params["radius"] == 8

    def test_all_actions_have_defaults(self):
        for action in ["zombie", "spiders", "slowness", "blindness", "creeper",
                       "storm", "randomtp", "explosion", "random", "chickens",
                       "give_item", "summon_mob", "apply_effect"]:
            req = build_action_with_defaults(action=action, target="Player1")
            assert isinstance(req, BridgeRequest)
            assert req.action == action

    def test_defaults_dict_completeness(self):
        expected_actions = {
            "zombie", "spiders", "slowness", "blindness", "creeper",
            "storm", "randomtp", "explosion", "random", "chickens",
            "give_item", "summon_mob", "apply_effect",
        }
        assert set(ACTION_PARAM_DEFAULTS.keys()) == expected_actions
