package com.chatcontrol.actions;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class ChickensBypassTest {

    @Test
    void testChickensBypassesCooldown() {
        ChickensAction chickens = new ChickensAction();
        assertTrue(chickens.bypassCooldown());
    }

    @Test
    void testChickensBypassesRateLimit() {
        ChickensAction chickens = new ChickensAction();
        assertTrue(chickens.bypassRateLimit());
    }

    @Test
    void testChickensCooldownIsZero() {
        ChickensAction chickens = new ChickensAction();
        assertEquals(0, chickens.getDefaultCooldownSeconds());
    }

    @Test
    void testChickensNotDangerous() {
        ChickensAction chickens = new ChickensAction();
        assertFalse(chickens.isDangerous());
    }

    @Test
    void testNormalActionsDoNotBypass() {
        ActionHandler zombie = new ActionHandler() {
            @Override public String getName() { return "zombie"; }
            @Override public String getDescription() { return ""; }
            @Override public boolean execute(net.minecraft.server.MinecraftServer server,
                    net.minecraft.server.network.ServerPlayerEntity target,
                    ActionParameters params) { return true; }
        };
        assertFalse(zombie.bypassCooldown());
        assertFalse(zombie.bypassRateLimit());
    }

    @Test
    void testDefaultBypassMethodsReturnFalse() {
        ActionHandler handler = new ActionHandler() {
            @Override public String getName() { return "test"; }
            @Override public String getDescription() { return ""; }
            @Override public boolean execute(net.minecraft.server.MinecraftServer server,
                    net.minecraft.server.network.ServerPlayerEntity target,
                    ActionParameters params) { return true; }
        };
        assertFalse(handler.bypassCooldown());
        assertFalse(handler.bypassRateLimit());
    }

    @Test
    void testAllRegisteredActionsExist() {
        ActionRegistry registry = new ActionRegistry();
        registry.register(new ChickensAction());

        String[] expectedActions = {"chickens"};
        for (String name : expectedActions) {
            assertNotNull(registry.getHandler(name), "Action not registered: " + name);
        }
    }
}
