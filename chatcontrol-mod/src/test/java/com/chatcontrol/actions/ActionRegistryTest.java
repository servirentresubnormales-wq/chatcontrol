package com.chatcontrol.actions;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class ActionRegistryTest {

    private ActionRegistry registry;

    @BeforeEach
    void setUp() {
        registry = new ActionRegistry();
    }

    @Test
    void testRegisterAndGet() {
        ActionHandler handler = createDummyHandler("test_action");
        registry.register(handler);
        assertEquals(handler, registry.getHandler("test_action"));
    }

    @Test
    void testGetUnknown() {
        assertNull(registry.getHandler("nonexistent"));
    }

    @Test
    void testIsRegistered() {
        assertFalse(registry.isRegistered("test_action"));
        registry.register(createDummyHandler("test_action"));
        assertTrue(registry.isRegistered("test_action"));
    }

    @Test
    void testGetRegisteredNames() {
        registry.register(createDummyHandler("a"));
        registry.register(createDummyHandler("b"));
        registry.register(createDummyHandler("c"));
        assertEquals(3, registry.getRegisteredNames().size());
        assertTrue(registry.getRegisteredNames().contains("a"));
        assertTrue(registry.getRegisteredNames().contains("b"));
        assertTrue(registry.getRegisteredNames().contains("c"));
    }

    @Test
    void testGetAllHandlers() {
        registry.register(createDummyHandler("x"));
        registry.register(createDummyHandler("y"));
        var all = registry.getAllHandlers();
        assertEquals(2, all.size());
        assertNotNull(all.get("x"));
        assertNotNull(all.get("y"));
    }

    @Test
    void testRegisterOverwrite() {
        ActionHandler h1 = createDummyHandler("same");
        ActionHandler h2 = createDummyHandler("same");
        registry.register(h1);
        registry.register(h2);
        assertEquals(h2, registry.getHandler("same"));
        assertEquals(1, registry.getRegisteredNames().size());
    }

    @Test
    void testUniqueIds() {
        for (int i = 0; i < 10; i++) {
            registry.register(createDummyHandler("action_" + i));
        }
        assertEquals(10, registry.getRegisteredNames().size());
    }

    private ActionHandler createDummyHandler(String name) {
        return new ActionHandler() {
            @Override public String getName() { return name; }
            @Override public String getDescription() { return "Test action"; }
            @Override public boolean execute(net.minecraft.server.MinecraftServer server,
                    net.minecraft.server.network.ServerPlayerEntity target,
                    ActionParameters params) { return true; }
        };
    }
}
