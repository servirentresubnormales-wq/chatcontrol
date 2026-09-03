package com.chatcontrol.protection;

import com.chatcontrol.actions.ActionParameters;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class SafetyCheckerBasicTest {

    @Test
    void testBlockedActions() {
        assertFalse(SafetyChecker.isActionAllowed("stop_server"));
        assertFalse(SafetyChecker.isActionAllowed("op_player"));
        assertFalse(SafetyChecker.isActionAllowed("deop_player"));
        assertFalse(SafetyChecker.isActionAllowed("ban_player"));
        assertFalse(SafetyChecker.isActionAllowed("whitelist"));
    }

    @Test
    void testAllowedActions() {
        assertTrue(SafetyChecker.isActionAllowed("zombie"));
        assertTrue(SafetyChecker.isActionAllowed("spiders"));
        assertTrue(SafetyChecker.isActionAllowed("explosion"));
        assertTrue(SafetyChecker.isActionAllowed("chickens"));
        assertTrue(SafetyChecker.isActionAllowed("random_teleport"));
    }

    @Test
    void testValidateParamsNull() {
        assertTrue(SafetyChecker.validateParams("zombie", null));
    }

    @Test
    void testIsCommandSafeNull() {
        assertFalse(SafetyChecker.isCommandSafe(null));
    }

    @Test
    void testIsCommandSafeEmpty() {
        assertFalse(SafetyChecker.isCommandSafe(""));
    }

    @Test
    void testIsCommandSafeDangerous() {
        assertFalse(SafetyChecker.isCommandSafe("stop"));
        assertFalse(SafetyChecker.isCommandSafe("op player"));
        assertFalse(SafetyChecker.isCommandSafe("deop player"));
        assertFalse(SafetyChecker.isCommandSafe("ban player"));
        assertFalse(SafetyChecker.isCommandSafe("whitelist on"));
        assertFalse(SafetyChecker.isCommandSafe("kill @a"));
        assertFalse(SafetyChecker.isCommandSafe("/fill 0 0 0 10 10 10 stone"));
        assertFalse(SafetyChecker.isCommandSafe("setblock 0 0 0 stone"));
        assertFalse(SafetyChecker.isCommandSafe("summon tnt 0 0 0"));
    }

    @Test
    void testIsCommandSafeSafe() {
        assertTrue(SafetyChecker.isCommandSafe("say hello"));
        assertTrue(SafetyChecker.isCommandSafe("gamemode creative @p"));
    }

    @Test
    void testSpidersAmountValidation() {
        ActionParameters validParams = new ActionParameters();
        validParams.set("amount", "5");
        assertTrue(SafetyChecker.validateParams("spiders", validParams));

        ActionParameters tooMany = new ActionParameters();
        tooMany.set("amount", "50");
        assertFalse(SafetyChecker.validateParams("spiders", tooMany));

        ActionParameters zeroAmount = new ActionParameters();
        zeroAmount.set("amount", "0");
        assertFalse(SafetyChecker.validateParams("spiders", zeroAmount));
    }

    @Test
    void testExplosionRadiusValidation() {
        ActionParameters validParams = new ActionParameters();
        validParams.set("radius", "3.0");
        assertTrue(SafetyChecker.validateParams("explosion", validParams));

        ActionParameters tooLarge = new ActionParameters();
        tooLarge.set("radius", "999");
        assertFalse(SafetyChecker.validateParams("explosion", tooLarge));

        ActionParameters tooSmall = new ActionParameters();
        tooSmall.set("radius", "0.1");
        assertFalse(SafetyChecker.validateParams("explosion", tooSmall));
    }

    @Test
    void testRandomTeleportRadiusValidation() {
        ActionParameters validParams = new ActionParameters();
        validParams.set("radius", "30");
        assertTrue(SafetyChecker.validateParams("random_teleport", validParams));

        ActionParameters tooLarge = new ActionParameters();
        tooLarge.set("radius", "500");
        assertFalse(SafetyChecker.validateParams("random_teleport", tooLarge));

        ActionParameters negative = new ActionParameters();
        negative.set("radius", "-10");
        assertFalse(SafetyChecker.validateParams("random_teleport", negative));
    }

    @Test
    void testChickensAmountValidation() {
        ActionParameters validParams = new ActionParameters();
        validParams.set("amount", "5");
        assertTrue(SafetyChecker.validateParams("chickens", validParams));

        ActionParameters tooMany = new ActionParameters();
        tooMany.set("amount", "20");
        assertFalse(SafetyChecker.validateParams("chickens", tooMany));
    }

    @Test
    void testSlownessValidation() {
        ActionParameters validParams = new ActionParameters();
        validParams.set("duration", "200");
        validParams.set("amplifier", "1");
        assertTrue(SafetyChecker.validateParams("slowness", validParams));

        ActionParameters badDuration = new ActionParameters();
        badDuration.set("duration", "99999");
        assertFalse(SafetyChecker.validateParams("slowness", badDuration));

        ActionParameters badAmplifier = new ActionParameters();
        badAmplifier.set("amplifier", "15");
        assertFalse(SafetyChecker.validateParams("slowness", badAmplifier));
    }

    @Test
    void testBlindnessValidation() {
        ActionParameters validParams = new ActionParameters();
        validParams.set("duration", "160");
        validParams.set("amplifier", "0");
        assertTrue(SafetyChecker.validateParams("blindness", validParams));

        ActionParameters badDuration = new ActionParameters();
        badDuration.set("duration", "-5");
        assertFalse(SafetyChecker.validateParams("blindness", badDuration));
    }
}
