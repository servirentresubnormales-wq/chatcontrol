import time
import pytest
from cooldowns.manager import CooldownManager


class TestCooldownManager:
    def test_no_cooldown_initially(self):
        cm = CooldownManager()
        assert not cm.is_on_cooldown("zombie")

    def test_apply_cooldown(self):
        cm = CooldownManager({"zombie": 10})
        cm.apply_cooldown("zombie")
        assert cm.is_on_cooldown("zombie")

    def test_cooldown_expires(self):
        cm = CooldownManager({"zombie": 0.1})
        cm.apply_cooldown("zombie")
        assert cm.is_on_cooldown("zombie")
        time.sleep(0.15)
        assert not cm.is_on_cooldown("zombie")

    def test_get_remaining(self):
        cm = CooldownManager({"zombie": 10})
        cm.apply_cooldown("zombie")
        remaining = cm.get_remaining("zombie")
        assert 9.0 < remaining <= 10.0

    def test_remaining_not_on_cooldown(self):
        cm = CooldownManager({"zombie": 10})
        assert cm.get_remaining("zombie") == 0.0

    def test_clear_cooldown(self):
        cm = CooldownManager({"zombie": 10})
        cm.apply_cooldown("zombie")
        assert cm.is_on_cooldown("zombie")
        cm.clear_cooldown("zombie")
        assert not cm.is_on_cooldown("zombie")

    def test_clear_all(self):
        cm = CooldownManager({"zombie": 10, "creeper": 10})
        cm.apply_cooldown("zombie")
        cm.apply_cooldown("creeper")
        cm.clear_all()
        assert not cm.is_on_cooldown("zombie")
        assert not cm.is_on_cooldown("creeper")

    def test_chickens_no_cooldown(self):
        cm = CooldownManager({"chickens": 10})
        cm.apply_cooldown("chickens")
        assert not cm.is_on_cooldown("chickens")

    def test_cleanup_expired(self):
        cm = CooldownManager({"zombie": 0.05})
        cm.apply_cooldown("zombie")
        time.sleep(0.1)
        removed = cm.cleanup_expired()
        assert removed == 1
        assert not cm.is_on_cooldown("zombie")

    def test_user_cooldown(self):
        cm = CooldownManager({"zombie": 10})
        cm.apply_cooldown("zombie", user="User1")
        assert cm.is_on_cooldown("zombie", user="User1")
        assert not cm.is_on_cooldown("zombie", user="User2")

    def test_platform_cooldown(self):
        cm = CooldownManager({"zombie": 10})
        cm.apply_cooldown("zombie", platform="twitch")
        assert cm.is_on_cooldown("zombie", platform="twitch")
        assert not cm.is_on_cooldown("zombie", platform="console")

    def test_set_cooldown(self):
        cm = CooldownManager()
        cm.set_cooldown("zombie", 20)
        cm.apply_cooldown("zombie")
        remaining = cm.get_remaining("zombie")
        assert 19.0 < remaining <= 20.0

    def test_custom_duration(self):
        cm = CooldownManager({"zombie": 10})
        cm.set_custom_duration("zombie", 30)
        cm.apply_cooldown("zombie")
        remaining = cm.get_remaining("zombie")
        assert 29.0 < remaining <= 30.0

    def test_zero_cooldown(self):
        cm = CooldownManager({"zombie": 0})
        cm.apply_cooldown("zombie")
        assert not cm.is_on_cooldown("zombie")

    def test_multiple_actions_independent(self):
        cm = CooldownManager({"zombie": 10, "creeper": 20})
        cm.apply_cooldown("zombie")
        cm.apply_cooldown("creeper")
        assert cm.is_on_cooldown("zombie")
        assert cm.is_on_cooldown("creeper")
        cm.clear_cooldown("zombie")
        assert not cm.is_on_cooldown("zombie")
        assert cm.is_on_cooldown("creeper")
